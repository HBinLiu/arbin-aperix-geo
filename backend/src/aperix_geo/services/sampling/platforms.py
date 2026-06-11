"""Resolve and validate sampling platform lists."""

from __future__ import annotations

from aperix_geo.config import Settings, get_settings
from aperix_geo.db.models import Subject
from aperix_geo.services.sampling.llm import configured_platforms, prefer_default_platforms


class SamplingPlatformError(ValueError):
    """Invalid or unavailable sampling platform selection."""


def resolve_subject_sampling_platforms(
    subject: Subject,
    *,
    settings: Settings | None = None,
) -> list[str]:
    """Empty subject config uses default platform; otherwise intersect with configured."""
    settings = settings or get_settings()
    available = configured_platforms(settings=settings)
    if not available:
        return []
    selected = [str(p).strip() for p in (subject.sampling_platforms or []) if str(p).strip()]
    if not selected:
        return prefer_default_platforms(settings=settings)
    valid = [p for p in selected if p in available]
    return valid or prefer_default_platforms(settings=settings)


def validate_explicit_sampling_platforms(
    platforms: list[str],
    *,
    settings: Settings | None = None,
    require_non_empty: bool = True,
) -> list[str]:
    """Dedupe and validate an explicit platform list against configured providers."""
    settings = settings or get_settings()
    available = configured_platforms(settings=settings)
    if not available:
        raise SamplingPlatformError("No LLM providers configured for sampling")
    deduped = list(dict.fromkeys(p.strip() for p in platforms if p.strip()))
    if require_non_empty and not deduped:
        raise SamplingPlatformError("至少选择一个平台")
    unknown = [p for p in deduped if p not in available]
    if unknown:
        raise SamplingPlatformError(f"Unknown or unconfigured platform(s): {', '.join(unknown)}")
    return deduped


def resolve_platforms_for_sampling(
    subject: Subject,
    requested: list[str] | None = None,
    *,
    settings: Settings | None = None,
) -> list[str]:
    """Explicit platforms when requested is non-empty; otherwise subject config or default."""
    settings = settings or get_settings()
    available = configured_platforms(settings=settings)
    if not available:
        raise SamplingPlatformError("No LLM providers configured for sampling")
    if requested:
        return validate_explicit_sampling_platforms(requested, settings=settings)
    return resolve_subject_sampling_platforms(subject, settings=settings)


def resolve_default_sampling_platforms(*, settings: Settings | None = None) -> list[str]:
    """First configured default platform (sync smoke test, no subject context)."""
    settings = settings or get_settings()
    available = configured_platforms(settings=settings)
    if not available:
        raise SamplingPlatformError("No LLM providers configured for sampling")
    return prefer_default_platforms(settings=settings)
