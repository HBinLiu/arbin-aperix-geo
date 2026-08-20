"""Multi-provider LLM routing for Dispatch (sampling)."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass

from aperix_geo.config import Settings, get_settings
from aperix_geo.services.providers.result import SamplingChatResult
from aperix_geo.services.providers.doubao import (
    DoubaoProviderError,
    doubao_chat_fallback,
    doubao_responses_chat,
)
from aperix_geo.services.providers.deepseek import deepseek_chat
from aperix_geo.services.providers.ernie import ernie_chat
from aperix_geo.services.providers.errors import ProviderError, parse_http_status_from_message
from aperix_geo.services.providers.kimi import kimi_chat
from aperix_geo.services.providers.qianwen import qianwen_generation_chat
from aperix_geo.services.providers.yuanbao import yuanbao_chat

logger = logging.getLogger(__name__)


def _message_indicates_timeout(message: str) -> bool:
    lower = message.lower()
    return "timeout" in lower or "timed out" in lower


class SamplingLLMError(Exception):
    """Any provider failure during sampling."""

    status_code: int | None
    retryable: bool | None

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        retryable: bool | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.retryable = retryable


def sampling_llm_error_from(exc: BaseException) -> SamplingLLMError:
    if isinstance(exc, SamplingLLMError):
        return exc
    status_code: int | None = None
    retryable: bool | None = None
    if isinstance(exc, ProviderError):
        status_code = exc.status_code
        retryable = exc.retryable
        if status_code is None:
            status_code = parse_http_status_from_message(str(exc))
        if retryable is None and _message_indicates_timeout(str(exc)):
            retryable = False
    elif isinstance(exc, TimeoutError):
        retryable = False
    elif isinstance(exc, (ConnectionError, OSError)):
        retryable = True
    return SamplingLLMError(str(exc), status_code=status_code, retryable=retryable)


@dataclass(frozen=True)
class SamplingPlatformSpec:
    platform: str
    label: str
    llm_model: Callable[[Settings], str]
    is_configured: Callable[[Settings], bool]
    rate_limit_per_minute: Callable[[Settings], int]
    chat: Callable[[list[dict[str, str]]], SamplingChatResult]


@dataclass(frozen=True)
class _PlatformDef:
    platform: str
    label: str
    prefix: str
    chat_factory: Callable[[Settings], Callable[[list[dict[str, str]]], SamplingChatResult]]


def _has_key(key: str) -> Callable[[Settings], bool]:
    return lambda s: bool(getattr(s, key, "").strip())


def _model(field: str) -> Callable[[Settings], str]:
    return lambda s: getattr(s, field, "").strip()


def _limit(field: str, default: int = 30) -> Callable[[Settings], int]:
    return lambda s: int(getattr(s, field, default) or default)


def _doubao_api_chat(messages: list[dict[str, str]], settings: Settings) -> SamplingChatResult:
    if settings.doubao_web_search_enabled:
        try:
            return doubao_responses_chat(
                messages,
                api_key=settings.doubao_api_key,
                base_url=settings.doubao_base_url,
                model=settings.doubao_model,
                web_search=True,
                timeout_s=settings.doubao_responses_timeout_s,
            )
        except DoubaoProviderError as exc:
            logger.warning("Doubao web search failed, fallback to chat/completions: %s", exc)
    return doubao_chat_fallback(
        messages,
        api_key=settings.doubao_api_key,
        base_url=settings.doubao_base_url,
        model=settings.doubao_model,
    )


def _doubao_crawl_sampling_complete(result: SamplingChatResult) -> bool:
    """Crawl payload is enough to finish sampling without share_url."""
    return bool((result.text or "").strip())


def _doubao_crawl_first_api_fallback(
    messages: list[dict[str, str]],
    settings: Settings,
    *,
    cause: str,
    exc: BaseException | None = None,
) -> SamplingChatResult:
    """When ``crawl_first`` browser crawl fails, fall back to Doubao HTTP API."""
    from aperix_geo.services.sampling.backends import crawl_first_mode, crawl_only_mode

    if crawl_only_mode("doubao", settings=settings):
        if exc is not None:
            raise SamplingLLMError(str(exc), retryable=False) from exc
        raise SamplingLLMError(cause, retryable=False)
    if not crawl_first_mode("doubao", settings=settings):
        if exc is not None:
            raise sampling_llm_error_from(exc) from exc
        raise SamplingLLMError(cause, retryable=False)
    if not (settings.doubao_api_key or "").strip():
        detail = cause if exc is None else f"{cause}: {exc}"
        raise SamplingLLMError(
            f"doubao crawl failed ({detail}) and API fallback unavailable (no doubao_api_key)",
            retryable=False,
        ) from exc
    logger.warning(
        "doubao_crawl_fallback reason=api_fallback mode=crawl_first cause=%s err=%s",
        cause,
        exc or "-",
    )
    return _doubao_api_chat(messages, settings)


def _doubao_chat(settings: Settings) -> Callable[[list[dict[str, str]]], SamplingChatResult]:
    """API-lane Doubao chat. Account-pool crawl runs on ``sampling_crawl`` workers."""

    def _call(messages: list[dict[str, str]]) -> SamplingChatResult:
        return _doubao_api_chat(messages, settings)

    return _call


def run_doubao_account_crawl(
    messages: list[dict[str, str]],
    *,
    settings: Settings | None = None,
) -> SamplingChatResult:
    """Account-pool crawl for the dedicated crawl Celery lane (busy→requeue, not API)."""
    settings = settings or get_settings()
    from aperix_geo.db.session import SessionLocal
    from aperix_geo.services.sampling.crawl_capacity import (
        CrawlCapacityBusy,
        CrawlPoolEmpty,
        crawl_capacity_slot,
    )
    from aperix_geo.services.providers.doubao_web.crawler import crawl_doubao_chat
    from aperix_geo.services.providers.doubao_web.errors import (
        DoubaoCaptchaRequired,
        DoubaoCrawlError,
        DoubaoNeedsHumanOps,
        DoubaoShareError,
    )

    db = SessionLocal()
    slot_cm = None
    slot_held = False
    try:
        slot_cm = crawl_capacity_slot(db, "doubao", settings=settings)
        slot_cm.__enter__()
        slot_held = True
    except CrawlPoolEmpty as exc:
        db.close()
        logger.warning(
            "doubao_crawl_fallback reason=no_credentials mode=%s event=sampling_crawl_lane",
            settings.doubao_sampling_mode,
        )
        return _doubao_crawl_first_api_fallback(
            messages, settings, cause="pool_empty", exc=exc
        )
    except CrawlCapacityBusy:
        db.close()
        raise
    except BaseException:
        db.close()
        raise
    else:
        db.close()

    def _drop_slot() -> None:
        nonlocal slot_held
        if slot_cm is None or not slot_held:
            return
        slot_held = False
        slot_cm.__exit__(None, None, None)

    try:
        try:
            result = crawl_doubao_chat(messages, settings=settings)
        except DoubaoCaptchaRequired as exc:
            # Open ops ticket asynchronously via crawl account path; sampling must
            # not wait for human solve — fall back to API immediately.
            logger.error(
                "doubao_crawl_fallback reason=captcha err=%s event=sampling_crawl_lane",
                exc,
            )
            _drop_slot()
            return _doubao_crawl_first_api_fallback(
                messages, settings, cause="captcha", exc=exc
            )
        except DoubaoNeedsHumanOps as exc:
            logger.error(
                "doubao_crawl_fallback reason=human_ops type=%s err=%s event=sampling_crawl_lane",
                type(exc).__name__,
                exc,
            )
            _drop_slot()
            return _doubao_crawl_first_api_fallback(
                messages, settings, cause="human_ops", exc=exc
            )
        except DoubaoShareError as exc:
            _drop_slot()
            logger.warning(
                "doubao crawl share failed without crawl payload (no API fallback) "
                "err=%s event=sampling_crawl_lane",
                exc,
            )
            raise SamplingLLMError(str(exc), retryable=False) from exc
        except DoubaoCrawlError as exc:
            logger.warning(
                "doubao_crawl_fallback reason=crawl_error err=%s event=sampling_crawl_lane",
                exc,
            )
            _drop_slot()
            return _doubao_crawl_first_api_fallback(
                messages, settings, cause="crawl_error", exc=exc
            )
        except Exception as exc:
            logger.warning(
                "doubao_crawl_fallback reason=unexpected err=%s event=sampling_crawl_lane",
                exc,
                exc_info=True,
            )
            _drop_slot()
            return _doubao_crawl_first_api_fallback(
                messages, settings, cause="unexpected", exc=exc
            )
        else:
            if not _doubao_crawl_sampling_complete(result):
                logger.warning(
                    "doubao_crawl_fallback reason=empty_text event=sampling_crawl_lane"
                )
                _drop_slot()
                return _doubao_crawl_first_api_fallback(
                    messages, settings, cause="empty_text"
                )
            if not (result.share_url or "").strip():
                logger.warning(
                    "doubao crawl sampling complete without share_url "
                    "(no API fallback) text_len=%s queries=%s sources=%s "
                    "event=sampling_crawl_lane",
                    len(result.text or ""),
                    len(result.search_queries),
                    len(result.source_urls),
                )
            return result
    finally:
        _drop_slot()


def _deepseek_chat(settings: Settings) -> Callable[[list[dict[str, str]]], SamplingChatResult]:
    def _call(messages: list[dict[str, str]]) -> SamplingChatResult:
        return deepseek_chat(
            messages,
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url,
            model=settings.deepseek_model,
            anthropic_base_url=settings.deepseek_anthropic_base_url,
            web_search=settings.deepseek_web_search_enabled,
            web_search_tool_type=settings.deepseek_web_search_tool_type,
            web_search_max_uses=settings.deepseek_web_search_max_uses,
            timeout_s=settings.deepseek_chat_timeout_s,
        )

    return _call


def _qianwen_chat(settings: Settings) -> Callable[[list[dict[str, str]]], SamplingChatResult]:
    def _call(messages: list[dict[str, str]]) -> SamplingChatResult:
        return qianwen_generation_chat(
            messages,
            api_key=settings.qianwen_api_key,
            base_url=settings.qianwen_base_url,
            model=settings.qianwen_model,
            web_search=settings.qianwen_web_search_enabled,
            timeout_s=settings.qianwen_generation_timeout_s,
        )

    return _call


def _yuanbao_chat(settings: Settings) -> Callable[[list[dict[str, str]]], SamplingChatResult]:
    def _call(messages: list[dict[str, str]]) -> SamplingChatResult:
        return yuanbao_chat(
            messages,
            api_key=settings.yuanbao_api_key,
            base_url=settings.yuanbao_base_url,
            model=settings.yuanbao_model,
            web_search=settings.yuanbao_web_search_enabled,
            timeout_s=settings.yuanbao_chat_timeout_s,
        )

    return _call


def _kimi_chat(settings: Settings) -> Callable[[list[dict[str, str]]], SamplingChatResult]:
    def _call(messages: list[dict[str, str]]) -> SamplingChatResult:
        return kimi_chat(
            messages,
            api_key=settings.kimi_api_key,
            base_url=settings.kimi_base_url,
            model=settings.kimi_model,
            web_search=settings.kimi_web_search_enabled,
            web_search_max_uses=settings.kimi_web_search_max_uses,
            timeout_s=settings.kimi_chat_timeout_s,
            temperature=settings.kimi_temperature,
        )

    return _call


def _ernie_chat(settings: Settings) -> Callable[[list[dict[str, str]]], SamplingChatResult]:
    def _call(messages: list[dict[str, str]]) -> SamplingChatResult:
        return ernie_chat(
            messages,
            api_key=settings.ernie_api_key,
            base_url=settings.ernie_base_url,
            model=settings.ernie_model,
            web_search=settings.ernie_web_search_enabled,
            timeout_s=settings.ernie_chat_timeout_s,
        )

    return _call


_PLATFORM_DEFS: tuple[_PlatformDef, ...] = (
    _PlatformDef("doubao", "豆包", "doubao", _doubao_chat),
    _PlatformDef("deepseek", "DeepSeek", "deepseek", _deepseek_chat),
    _PlatformDef("qianwen", "通义千问", "qianwen", _qianwen_chat),
    _PlatformDef("yuanbao", "腾讯元宝", "yuanbao", _yuanbao_chat),
    _PlatformDef("kimi", "Kimi", "kimi", _kimi_chat),
    _PlatformDef("ernie", "文心一言", "ernie", _ernie_chat),
)

_cached_specs: list[SamplingPlatformSpec] | None = None
_cached_settings_id: int | None = None


def _build_specs(settings: Settings) -> list[SamplingPlatformSpec]:
    specs: list[SamplingPlatformSpec] = []
    for defn in _PLATFORM_DEFS:
        api_key_field = f"{defn.prefix}_api_key"
        if not getattr(settings, api_key_field, "").strip():
            continue
        specs.append(
            SamplingPlatformSpec(
                platform=defn.platform,
                label=defn.label,
                llm_model=_model(f"{defn.prefix}_model"),
                is_configured=_has_key(api_key_field),
                rate_limit_per_minute=_limit(f"{defn.prefix}_rate_limit_per_minute"),
                chat=defn.chat_factory(settings),
            )
        )
    return specs


def _get_specs(settings: Settings) -> list[SamplingPlatformSpec]:
    global _cached_specs, _cached_settings_id
    sid = id(settings)
    if _cached_specs is None or _cached_settings_id != sid:
        _cached_specs = _build_specs(settings)
        _cached_settings_id = sid
    return _cached_specs


def list_sampling_platforms(*, settings: Settings | None = None) -> list[dict[str, str]]:
    s = settings or get_settings()
    out: list[dict[str, str]] = []
    for spec in _get_specs(s):
        if spec.is_configured(s):
            out.append({"platform": spec.platform, "label": spec.label})
    return out


def configured_platforms(*, settings: Settings | None = None) -> list[str]:
    return [p["platform"] for p in list_sampling_platforms(settings=settings)]


DEFAULT_SAMPLING_PROVIDER = "doubao"


def prefer_default_platforms(*, settings: Settings | None = None) -> list[str]:
    """主体未配置平台时的默认采样平台（优先豆包）。"""
    platforms = list_sampling_platforms(settings=settings)
    if not platforms:
        return []
    for item in platforms:
        if item["platform"] == DEFAULT_SAMPLING_PROVIDER:
            return [DEFAULT_SAMPLING_PROVIDER]
    return [platforms[0]["platform"]]


def resolve_sampling_platform(platform: str, *, settings: Settings | None = None) -> SamplingPlatformSpec:
    s = settings or get_settings()
    for spec in _get_specs(s):
        if spec.is_configured(s) and spec.platform == platform:
            return spec
    raise SamplingLLMError(f"Unknown or unconfigured platform: {platform}")


def llm_model_for_platform(platform: str, *, settings: Settings | None = None) -> str:
    return resolve_sampling_platform(platform, settings=settings).llm_model(settings or get_settings())


def chat_for_platform(
    platform: str,
    messages: list[dict[str, str]],
    *,
    settings: Settings | None = None,
) -> SamplingChatResult:
    spec = resolve_sampling_platform(platform, settings=settings)
    try:
        result = spec.chat(messages)
        from aperix_geo.services.alerts.dispatch import maybe_report_provider_success

        maybe_report_provider_success(spec.platform, settings=settings or get_settings())
        return result
    except ProviderError as e:
        raise sampling_llm_error_from(e) from e
    except SamplingLLMError:
        raise
    except Exception as e:
        raise sampling_llm_error_from(e) from e


def rate_limit_for_platform(platform: str, *, settings: Settings | None = None) -> tuple[str, int]:
    spec = resolve_sampling_platform(platform, settings=settings)
    s = settings or get_settings()
    return spec.platform, spec.rate_limit_per_minute(s)
