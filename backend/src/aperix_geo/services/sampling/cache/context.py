"""Job-window cache for subject/competitor and prompt text during sampling."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from aperix_geo.db.models import Competitor, LLMResponse, LLMResponseStatus, Prompt, SamplingJob, Subject, SubjectType
from aperix_geo.services.subject.loader import load_subject_with_competitors
from aperix_geo.utils.cache import TieredJsonCache

_SAMPLING_CONTEXT_CACHE_TTL_S = 600
_SUBJECT_CACHE = TieredJsonCache(
    redis_prefix="aperix:sampling:subject:v2:",
    l1_max_entries=128,
    use_remaining_ttl=False,
)
_PROMPT_CACHE = TieredJsonCache(
    redis_prefix="aperix:sampling:prompt_text:v1:",
    l1_max_entries=512,
    use_remaining_ttl=False,
)


def _serialize_subject(subject: Subject) -> dict[str, Any]:
    return {
        "id": str(subject.id),
        "tenant_id": str(subject.tenant_id),
        "type": subject.type.value,
        "domain": subject.domain or "",
        "brand": subject.brand or "",
        "aliases": list(subject.aliases or []),
        "website_url": subject.website_url or "",
        "niche_profile": dict(subject.niche_profile or {}),
        "competitors": [
            {
                "id": str(c.id),
                "subject_id": str(c.subject_id),
                "brand": c.brand or "",
                "domain": c.domain or "",
                "aliases": list(c.aliases or []),
            }
            for c in (subject.competitors or [])
        ],
    }


def _deserialize_subject(data: dict[str, Any]) -> Subject:
    subject = Subject(
        id=UUID(str(data["id"])),
        tenant_id=UUID(str(data["tenant_id"])),
        type=SubjectType(str(data["type"])),
        domain=str(data.get("domain") or ""),
        brand=str(data.get("brand") or ""),
        aliases=list(data.get("aliases") or []),
        website_url=str(data.get("website_url") or ""),
    )
    niche = data.get("niche_profile")
    subject.niche_profile = dict(niche) if isinstance(niche, dict) else {}
    competitors: list[Competitor] = []
    for row in data.get("competitors") or []:
        if not isinstance(row, dict):
            continue
        competitors.append(
            Competitor(
                id=UUID(str(row["id"])),
                subject_id=UUID(str(row["subject_id"])),
                brand=str(row.get("brand") or ""),
                domain=str(row.get("domain") or ""),
                aliases=list(row.get("aliases") or []),
            )
        )
    subject.competitors = competitors
    return subject


def _cache_subject(subject: Subject, *, ttl_s: int) -> None:
    _SUBJECT_CACHE.set(str(subject.id), _serialize_subject(subject), ttl_s=ttl_s)


def _cache_prompt_text(prompt_id: UUID, text: str, *, ttl_s: int) -> None:
    _PROMPT_CACHE.set(str(prompt_id), {"text": text}, ttl_s=ttl_s)


def load_subject_with_competitors_cached(
    db: Session,
    subject_id: UUID,
    *,
    tenant_id: UUID | None = None,
    ttl_s: int = _SAMPLING_CONTEXT_CACHE_TTL_S,
) -> Subject | None:
    """Load subject + competitors; prefer L1/Redis over DB within a sampling job window."""
    key = str(subject_id)
    payload = _SUBJECT_CACHE.get(
        key,
        default_ttl_s=ttl_s,
        is_valid=lambda data: bool(data.get("id")),
    )
    if payload is not None:
        return _deserialize_subject(payload)

    subject = load_subject_with_competitors(db, subject_id, tenant_id=tenant_id)
    if subject is not None:
        _cache_subject(subject, ttl_s=ttl_s)
    return subject


def load_prompt_text_cached(
    db: Session,
    prompt_id: UUID,
    *,
    ttl_s: int = _SAMPLING_CONTEXT_CACHE_TTL_S,
) -> str | None:
    """Load prompt text; prefer L1/Redis over DB."""
    key = str(prompt_id)
    payload = _PROMPT_CACHE.get(
        key,
        default_ttl_s=ttl_s,
        is_valid=lambda data: "text" in data,
    )
    if payload is not None:
        return str(payload["text"])

    prompt = db.get(Prompt, prompt_id)
    if prompt is None:
        return None
    _cache_prompt_text(prompt_id, prompt.text, ttl_s=ttl_s)
    return prompt.text


def warm_sampling_job_context(
    db: Session,
    *,
    job_id: UUID,
    ttl_s: int = _SAMPLING_CONTEXT_CACHE_TTL_S,
) -> None:
    """Prefetch subject and prompt texts for pending rows before chord dispatch."""
    job = db.get(SamplingJob, job_id)
    if job is None:
        return

    subject = load_subject_with_competitors(db, job.subject_id)
    if subject is not None:
        _cache_subject(subject, ttl_s=ttl_s)

    prompt_ids = set(
        db.execute(
            select(LLMResponse.prompt_id).where(
                LLMResponse.sampling_job_id == job_id,
                LLMResponse.status == LLMResponseStatus.pending,
            )
        ).scalars().all()
    )
    if not prompt_ids:
        return

    for prompt in db.execute(select(Prompt).where(Prompt.id.in_(prompt_ids))).scalars().all():
        _cache_prompt_text(prompt.id, prompt.text, ttl_s=ttl_s)


def clear_sampling_context_cache() -> None:
    """Test helper."""
    _SUBJECT_CACHE.clear()
    _PROMPT_CACHE.clear()


def clear_subject_sampling_cache(subject_id: UUID) -> None:
    """Drop cached subject row after competitor list changes."""
    _SUBJECT_CACHE.delete(str(subject_id))
