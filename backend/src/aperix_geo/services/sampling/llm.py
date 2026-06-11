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
    elif isinstance(exc, (TimeoutError, ConnectionError, OSError)):
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


def _doubao_chat(settings: Settings) -> Callable[[list[dict[str, str]]], SamplingChatResult]:
    def _call(messages: list[dict[str, str]]) -> SamplingChatResult:
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

    return _call


def _deepseek_chat(settings: Settings) -> Callable[[list[dict[str, str]]], SamplingChatResult]:
    def _call(messages: list[dict[str, str]]) -> SamplingChatResult:
        return deepseek_chat(
            messages,
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url,
            model=settings.deepseek_model,
            web_search=settings.deepseek_web_search_enabled,
            searxng_max_results=settings.sampling_searxng_max_results,
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
            searxng_max_results=settings.sampling_searxng_max_results,
            timeout_s=settings.kimi_chat_timeout_s,
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
        return spec.chat(messages)
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
