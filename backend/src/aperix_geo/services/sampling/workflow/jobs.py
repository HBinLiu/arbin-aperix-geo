"""Create sampling jobs and enqueue Celery orchestration."""

from __future__ import annotations

from typing import NoReturn
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from aperix_geo.config import Settings
from aperix_geo.db.models import (
    LLMResponse,
    LLMResponseStatus,
    Prompt,
    SamplingJob,
    SamplingJobStatus,
    Subject,
)
from aperix_geo.services.billing.exceptions import QuotaExceededError, SubscriptionInactiveError
from aperix_geo.services.billing.quota import lock_tenant_ai_quota, require_active_subscription, reserve_ai_usage
from aperix_geo.services.sampling.platforms import (
    SamplingPlatformError,
    resolve_platforms_for_sampling as _resolve_platforms_for_sampling,
)
from aperix_geo.services.sampling.workflow.schedule import subject_has_active_sampling_job
from aperix_geo.services.subject.rules import validate_brand_competitors, validate_subject_fields

_SUBSCRIPTION_EXPIRED_MSG = "订阅已过期，无法开始采样"
_AI_QUOTA_INSUFFICIENT_MSG = "AI 调用额度不足，无法开始采样"

SAMPLING_ERR_SUBSCRIPTION_INACTIVE = "subscription_inactive"
SAMPLING_ERR_QUOTA_INSUFFICIENT = "quota_insufficient"
SAMPLING_ERR_CONFLICT = "conflict"


def _platform_first_pairs(
    prompts: list[Prompt],
    platforms: list[str],
) -> list[tuple[Prompt, str]]:
    """Order sampling items platform-first, then prompt order within each platform."""
    return [(prompt, platform) for platform in platforms for prompt in prompts]


class SamplingJobError(ValueError):
    """Business rule violation when creating a sampling job."""

    def __init__(self, message: str, *, code: str = SAMPLING_ERR_CONFLICT) -> None:
        super().__init__(message)
        self.code = code


def raise_sampling_unavailable(
    db: Session,
    tenant_id: UUID,
    *,
    expired_msg: str,
    quota_msg: str,
) -> NoReturn:
    """After available==0: distinguish expired subscription vs empty AI quota."""
    try:
        require_active_subscription(db, tenant_id)
    except SubscriptionInactiveError as e:
        raise SamplingJobError(expired_msg, code=SAMPLING_ERR_SUBSCRIPTION_INACTIVE) from e
    raise SamplingJobError(quota_msg, code=SAMPLING_ERR_QUOTA_INSUFFICIENT)


def resolve_platforms_for_sampling(
    subject: Subject,
    requested: list[str] | None = None,
    *,
    settings: Settings | None = None,
) -> list[str]:
    try:
        return _resolve_platforms_for_sampling(subject, requested, settings=settings)
    except SamplingPlatformError as e:
        raise SamplingJobError(str(e)) from e


def create_and_enqueue_sampling_job(
    db: Session,
    *,
    subject: Subject,
    tenant_id: UUID,
    prompt_ids: list[UUID] | None = None,
    platforms: list[str] | None = None,
    update_schedule_anchor: bool = False,
) -> SamplingJob:
    try:
        require_active_subscription(db, tenant_id)
    except SubscriptionInactiveError as e:
        raise SamplingJobError(
            _SUBSCRIPTION_EXPIRED_MSG, code=SAMPLING_ERR_SUBSCRIPTION_INACTIVE
        ) from e

    resolved_platforms = platforms if platforms is not None else resolve_platforms_for_sampling(subject)
    if not resolved_platforms:
        raise SamplingJobError("No LLM providers configured for sampling")

    q = select(Prompt).where(Prompt.subject_id == subject.id, Prompt.enabled.is_(True))
    if prompt_ids:
        q = q.where(Prompt.id.in_(prompt_ids))
    # Fanout prompts start disabled; once enabled they join auto sampling with roots.
    prompts = list(db.execute(q).scalars().all())
    if not prompts:
        raise SamplingJobError("No enabled prompts to sample")

    locked_subject = db.execute(
        select(Subject).where(Subject.id == subject.id).with_for_update()
    ).scalar_one_or_none()
    if locked_subject is None:
        raise SamplingJobError("Subject not found")
    if subject_has_active_sampling_job(db, subject.id):
        raise SamplingJobError("A sampling job is already queued or running for this subject")

    # Hold tenant quota locks until commit so available → truncate → reserve is atomic.
    available = lock_tenant_ai_quota(db, tenant_id)
    if available <= 0:
        db.rollback()
        raise_sampling_unavailable(
            db,
            tenant_id,
            expired_msg=_SUBSCRIPTION_EXPIRED_MSG,
            quota_msg=_AI_QUOTA_INSUFFICIENT_MSG,
        )

    pairs = _platform_first_pairs(prompts, resolved_platforms)
    if available < len(pairs):
        pairs = pairs[:available]
    total_items = len(pairs)

    job = SamplingJob(
        tenant_id=tenant_id,
        subject_id=subject.id,
        status=SamplingJobStatus.queued,
        total_items=total_items,
    )
    db.add(job)
    db.flush()

    for prompt, platform in pairs:
        db.add(
            LLMResponse(
                sampling_job_id=job.id,
                prompt_id=prompt.id,
                platform=platform,
                status=LLMResponseStatus.pending,
            )
        )

    try:
        # Reuses the same transaction locks acquired above.
        reserve_ai_usage(db, tenant_id=tenant_id, amount=total_items, job=job)
    except QuotaExceededError as e:
        db.rollback()
        raise SamplingJobError(
            _AI_QUOTA_INSUFFICIENT_MSG, code=SAMPLING_ERR_QUOTA_INSUFFICIENT
        ) from e

    if update_schedule_anchor:
        from aperix_geo.services.sampling.workflow.schedule import remember_schedule_anchor_for_job

        remember_schedule_anchor_for_job(job.id, subject_id=subject.id)

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
