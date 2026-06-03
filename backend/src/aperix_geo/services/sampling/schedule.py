"""Scheduled sampling: interval validation and due-subject selection."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from aperix_geo.db.models import Prompt, SamplingJob, SamplingJobStatus, Subject

ALLOWED_SAMPLING_INTERVAL_HOURS = frozenset({0, 6, 12, 24, 72, 168})
DEFAULT_SAMPLING_INTERVAL_HOURS = 24


def validate_sampling_interval(hours: int) -> int:
    if hours not in ALLOWED_SAMPLING_INTERVAL_HOURS:
        allowed = ", ".join(str(h) for h in sorted(ALLOWED_SAMPLING_INTERVAL_HOURS))
        raise ValueError(f"sampling_interval must be one of: {allowed}")
    return hours


def get_latest_sampling_job(db: Session, subject_id: UUID) -> SamplingJob | None:
    return db.execute(
        select(SamplingJob)
        .where(SamplingJob.subject_id == subject_id)
        .order_by(desc(SamplingJob.created_at))
        .limit(1)
    ).scalar_one_or_none()


def subject_has_active_sampling_job(db: Session, subject_id: UUID) -> bool:
    job = get_latest_sampling_job(db, subject_id)
    if not job:
        return False
    return job.status in (SamplingJobStatus.queued, SamplingJobStatus.running)


def subject_has_enabled_prompts(db: Session, subject_id: UUID) -> bool:
    row = db.execute(
        select(Prompt.id)
        .where(Prompt.subject_id == subject_id, Prompt.enabled.is_(True))
        .limit(1)
    ).scalar_one_or_none()
    return row is not None


def is_subject_due_for_scheduled_sampling(subject: Subject, *, now: datetime | None = None) -> bool:
    if subject.sampling_interval <= 0:
        return False
    now = now or datetime.now(UTC)
    anchor = subject.last_sampled_at or subject.created_at
    if anchor.tzinfo is None:
        anchor = anchor.replace(tzinfo=UTC)
    return now >= anchor + timedelta(hours=subject.sampling_interval)


def find_subjects_due_for_scheduled_sampling(db: Session, *, now: datetime | None = None) -> list[Subject]:
    now = now or datetime.now(UTC)
    subjects = list(db.execute(select(Subject).where(Subject.sampling_interval > 0)).scalars().all())
    due: list[Subject] = []
    for subject in subjects:
        if not is_subject_due_for_scheduled_sampling(subject, now=now):
            continue
        if subject_has_active_sampling_job(db, subject.id):
            continue
        if not subject_has_enabled_prompts(db, subject.id):
            continue
        due.append(subject)
    return due
