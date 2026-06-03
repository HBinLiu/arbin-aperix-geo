"""Resolve sampling platforms for a subject."""

from __future__ import annotations

from fastapi import HTTPException, status

from aperix_geo.config import Settings, get_settings
from aperix_geo.db.models import Subject
from aperix_geo.services.sampling.llm import configured_platforms, prefer_default_platforms


def resolve_subject_sampling_platforms(
    subject: Subject,
    *,
    settings: Settings | None = None,
) -> list[str]:
    """空列表表示使用默认平台；否则取与已配置平台的交集，无效时回退默认。"""
    settings = settings or get_settings()
    available = configured_platforms(settings=settings)
    if not available:
        return []
    selected = [str(p).strip() for p in (subject.sampling_platforms or []) if str(p).strip()]
    if not selected:
        return prefer_default_platforms(settings=settings)
    valid = [p for p in selected if p in available]
    return valid or prefer_default_platforms(settings=settings)


def validate_sampling_platforms(
    platforms: list[str],
    *,
    settings: Settings | None = None,
) -> list[str]:
    settings = settings or get_settings()
    available = configured_platforms(settings=settings)
    if not available:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No LLM providers configured for sampling",
        )
    deduped = list(dict.fromkeys(p.strip() for p in platforms if p.strip()))
    if not deduped:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="至少选择一个平台")
    unknown = [p for p in deduped if p not in available]
    if unknown:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown or unconfigured platform(s): {', '.join(unknown)}",
        )
    return deduped
