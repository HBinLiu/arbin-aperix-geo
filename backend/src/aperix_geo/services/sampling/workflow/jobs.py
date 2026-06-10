"""Create sampling jobs and enqueue Celery orchestration."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from aperix_geo.config import Settings, get_settings
from aperix_geo.db.models import (
    LLMResponse,
    LLMResponseStatus,
    Prompt,
    SamplingJob,
    SamplingJobStatus,
    Subject,
)
from aperix_geo.services.sampling.llm import configured_platforms, prefer_default_platforms
from aperix_geo.services.sampling.subject import resolve_subject_sampling_platforms
from aperix_geo.services.subject.rules import validate_brand_competitors, validate_subject_fields


class SamplingJobError(ValueError):
    """Business rule violation when creating a sampling job."""


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
        raise SamplingJobError("No LLM providers configured for sampling")
    if requested:
        deduped = list(dict.fromkeys(p.strip() for p in requested if p.strip()))
        unknown = [p for p in deduped if p not in available]
        if unknown:
            raise SamplingJobError(f"Unknown or unconfigured platform(s): {', '.join(unknown)}")
        return deduped
    return resolve_subject_sampling_platforms(subject, settings=settings)


def resolve_default_sampling_platforms(*, settings: Settings | None = None) -> list[str]:
    """First configured default platform (sync smoke test, no subject context)."""
    settings = settings or get_settings()
    available = configured_platforms(settings=settings)
    if not available:
        raise SamplingJobError("No LLM providers configured for sampling")
    return prefer_default_platforms(settings=settings)


def create_and_enqueue_sampling_job(
    db: Session,
    *,
    subject: Subject,
    tenant_id: UUID,
    prompt_ids: list[UUID] | None = None,
    platforms: list[str] | None = None,
    update_schedule_anchor: bool = False,
) -> SamplingJob:
    resolved_platforms = platforms if platforms is not None else resolve_platforms_for_sampling(subject)
    if not resolved_platforms:
        raise SamplingJobError("No LLM providers configured for sampling")

    q = select(Prompt).where(Prompt.subject_id == subject.id, Prompt.enabled.is_(True))
    if prompt_ids:
        q = q.where(Prompt.id.in_(prompt_ids))
    prompts = list(db.execute(q).scalars().all())
    if not prompts:
        raise SamplingJobError("No enabled prompts to sample")

    job = SamplingJob(
        tenant_id=tenant_id,
        subject_id=subject.id,
        status=SamplingJobStatus.queued,
        total_items=len(prompts) * len(resolved_platforms),
    )
    db.add(job)
    db.flush()

    for prompt in prompts:
        for platform in resolved_platforms:
            db.add(
                LLMResponse(
                    sampling_job_id=job.id,
                    prompt_id=prompt.id,
                    platform=platform,
                    status=LLMResponseStatus.pending,
                )
            )

    if update_schedule_anchor:
        subject.last_sampled_at = datetime.now(UTC)

    db.commit()
    db.refresh(job)
    from aperix_geo.services.sampling.workflow.orchestrate import enqueue_sampling_orchestration

    enqueue_sampling_orchestration(job.id)
    return job


def enqueue_subject_sampling(
    db: Session,
    *,
    subject: Subject,
    tenant_id: UUID | None = None,
    prompt_ids: list[UUID] | None = None,
    platforms: list[str] | None = None,
    update_schedule_anchor: bool = False,
    validate: bool = True,
) -> SamplingJob:
    """Validate subject, resolve platforms, create job, and enqueue workers."""
    if validate:
        validate_subject_fields(subject)
        validate_brand_competitors(subject)
    resolved = resolve_platforms_for_sampling(subject, platforms)
    return create_and_enqueue_sampling_job(
        db,
        subject=subject,
        tenant_id=tenant_id or subject.tenant_id,
        prompt_ids=prompt_ids,
        platforms=resolved,
        update_schedule_anchor=update_schedule_anchor,
    )
