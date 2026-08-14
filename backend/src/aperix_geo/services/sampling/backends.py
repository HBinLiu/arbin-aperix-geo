"""Sampling execution backend: API lane vs account-pool crawl lane."""

from __future__ import annotations

from typing import Literal

from aperix_geo.config import Settings, get_settings

SamplingBackend = Literal["api", "crawl"]

# Platforms that can run account-pool browser sampling when mode allows.
_CRAWL_CAPABLE_PLATFORMS = frozenset({"doubao"})


def platform_supports_crawl_backend(platform: str) -> bool:
    return (platform or "").strip().lower() in _CRAWL_CAPABLE_PLATFORMS


def resolve_sampling_backend(
    platform: str,
    *,
    settings: Settings | None = None,
) -> SamplingBackend:
    """Return which Celery lane should produce the chat sample for ``platform``."""
    settings = settings or get_settings()
    plat = (platform or "").strip().lower()
    if not platform_supports_crawl_backend(plat):
        return "api"
    if plat == "doubao":
        mode = (settings.doubao_sampling_mode or "api_only").strip().lower()
        if mode in ("crawl_first", "crawl_only"):
            return "crawl"
        return "api"
    return "api"


def crawl_only_mode(platform: str, *, settings: Settings | None = None) -> bool:
    settings = settings or get_settings()
    plat = (platform or "").strip().lower()
    if plat == "doubao":
        return (settings.doubao_sampling_mode or "").strip().lower() == "crawl_only"
    return False


def crawl_first_mode(platform: str, *, settings: Settings | None = None) -> bool:
    settings = settings or get_settings()
    plat = (platform or "").strip().lower()
    if plat == "doubao":
        return (settings.doubao_sampling_mode or "").strip().lower() == "crawl_first"
    return False
