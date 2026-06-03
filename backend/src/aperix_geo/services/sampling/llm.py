"""Multi-provider LLM routing for Dispatch (sampling)."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from aperix_geo.config import Settings, get_settings
from aperix_geo.services.providers import LLMProviderError, chat_completion
from aperix_geo.services.providers.openai import openai_chat_completion
from aperix_geo.services.providers.yuanbao import YuanbaoProviderError, yuanbao_chat_completion


class SamplingLLMError(Exception):
    """Any provider failure during sampling."""


@dataclass(frozen=True)
class SamplingPlatformSpec:
    platform: str
    label: str
    llm_model: Callable[[Settings], str]
    is_configured: Callable[[Settings], bool]
    rate_limit_per_minute: Callable[[Settings], int]
    chat: Callable[[list[dict[str, str]]], tuple[str, dict[str, Any], int]]


def _has_key(key: str) -> Callable[[Settings], bool]:
    return lambda s: bool(getattr(s, key, "").strip())


def _model(field: str) -> Callable[[Settings], str]:
    return lambda s: getattr(s, field, "").strip()


def _limit(field: str, default: int = 30) -> Callable[[Settings], int]:
    return lambda s: int(getattr(s, field, default) or default)


def _openai_provider_chat(
    *,
    settings: Settings,
    provider_label: str,
    api_key: str,
    base_url: str,
    path: str,
    model: str,
    error_cls: type[Exception],
) -> Callable[[list[dict[str, str]]], tuple[str, dict[str, Any], int]]:
    url = base_url.rstrip("/") + path

    def _call(messages: list[dict[str, str]]) -> tuple[str, dict[str, Any], int]:
        return openai_chat_completion(
            url=url,
            api_key=api_key,
            model=model,
            messages=messages,
            error_cls=error_cls,
            provider_label=provider_label,
        )

    return _call


def _build_specs(settings: Settings) -> list[SamplingPlatformSpec]:
    specs: list[SamplingPlatformSpec] = []

    if settings.doubao_api_key.strip():
        specs.append(
            SamplingPlatformSpec(
                platform="doubao",
                label="豆包",
                llm_model=_model("doubao_model"),
                is_configured=_has_key("doubao_api_key"),
                rate_limit_per_minute=_limit("doubao_rate_limit_per_minute"),
                chat=_openai_provider_chat(
                    settings=settings,
                    provider_label="Doubao",
                    api_key=settings.doubao_api_key,
                    base_url=settings.doubao_base_url,
                    path="/chat/completions",
                    model=settings.doubao_model,
                    error_cls=SamplingLLMError,
                ),
            )
        )

    if settings.deepseek_api_key.strip():
        specs.append(
            SamplingPlatformSpec(
                platform="deepseek",
                label="DeepSeek",
                llm_model=_model("deepseek_model"),
                is_configured=_has_key("deepseek_api_key"),
                rate_limit_per_minute=_limit("deepseek_rate_limit_per_minute"),
                chat=lambda messages, s=settings: chat_completion(messages),
            )
        )

    if settings.qianwen_api_key.strip():
        specs.append(
            SamplingPlatformSpec(
                platform="qianwen",
                label="通义千问",
                llm_model=_model("qianwen_model"),
                is_configured=_has_key("qianwen_api_key"),
                rate_limit_per_minute=_limit("qianwen_rate_limit_per_minute"),
                chat=_openai_provider_chat(
                    settings=settings,
                    provider_label="Qianwen",
                    api_key=settings.qianwen_api_key,
                    base_url=settings.qianwen_base_url,
                    path="/chat/completions",
                    model=settings.qianwen_model,
                    error_cls=SamplingLLMError,
                ),
            )
        )

    if settings.yuanbao_api_key.strip():
        specs.append(
            SamplingPlatformSpec(
                platform="yuanbao",
                label="腾讯元宝",
                llm_model=_model("yuanbao_model"),
                is_configured=_has_key("yuanbao_api_key"),
                rate_limit_per_minute=_limit("yuanbao_rate_limit_per_minute"),
                chat=lambda messages: yuanbao_chat_completion(messages),
            )
        )

    if settings.kimi_api_key.strip():
        specs.append(
            SamplingPlatformSpec(
                platform="kimi",
                label="Kimi",
                llm_model=_model("kimi_model"),
                is_configured=_has_key("kimi_api_key"),
                rate_limit_per_minute=_limit("kimi_rate_limit_per_minute"),
                chat=_openai_provider_chat(
                    settings=settings,
                    provider_label="Kimi",
                    api_key=settings.kimi_api_key,
                    base_url=settings.kimi_base_url,
                    path="/chat/completions",
                    model=settings.kimi_model,
                    error_cls=SamplingLLMError,
                ),
            )
        )

    if settings.ernie_api_key.strip():
        specs.append(
            SamplingPlatformSpec(
                platform="ernie",
                label="文心一言",
                llm_model=_model("ernie_model"),
                is_configured=_has_key("ernie_api_key"),
                rate_limit_per_minute=_limit("ernie_rate_limit_per_minute"),
                chat=_openai_provider_chat(
                    settings=settings,
                    provider_label="Ernie",
                    api_key=settings.ernie_api_key,
                    base_url=settings.ernie_base_url,
                    path="/chat/completions",
                    model=settings.ernie_model,
                    error_cls=SamplingLLMError,
                ),
            )
        )

    return specs


def list_sampling_platforms(*, settings: Settings | None = None) -> list[dict[str, str]]:
    s = settings or get_settings()
    out: list[dict[str, str]] = []
    for spec in _build_specs(s):
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
    for spec in _build_specs(s):
        if spec.is_configured(s) and spec.platform == platform:
            return spec
    raise SamplingLLMError(f"Unknown or unconfigured platform: {platform}")


def llm_model_for_platform(platform: str, *, settings: Settings | None = None) -> str:
    return resolve_sampling_platform(platform, settings=settings).llm_model(settings or get_settings())


def platform_for_llm_model(llm_model: str, *, settings: Settings | None = None) -> str | None:
    s = settings or get_settings()
    for spec in _build_specs(s):
        if spec.is_configured(s) and spec.llm_model(s) == llm_model:
            return spec.platform
    return None


def chat_for_platform(
    platform: str,
    messages: list[dict[str, str]],
    *,
    settings: Settings | None = None,
) -> tuple[str, dict[str, Any], int]:
    spec = resolve_sampling_platform(platform, settings=settings)
    try:
        return spec.chat(messages)
    except (LLMProviderError, YuanbaoProviderError) as e:
        raise SamplingLLMError(str(e)) from e
    except SamplingLLMError:
        raise
    except Exception as e:
        raise SamplingLLMError(str(e)) from e


def rate_limit_for_platform(platform: str, *, settings: Settings | None = None) -> tuple[str, int]:
    spec = resolve_sampling_platform(platform, settings=settings)
    s = settings or get_settings()
    return spec.platform, spec.rate_limit_per_minute(s)
