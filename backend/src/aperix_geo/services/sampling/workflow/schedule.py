"""Scheduled sampling: daily window + per-subject slot within window."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from aperix_geo.config import Settings, get_settings
from aperix_geo.db.models import Prompt, SamplingJob, SamplingJobStatus, Subject

# 固定北京时间；「今日是否已采样」与每日窗口均按此计算
SAMPLING_TIMEZONE = "Asia/Shanghai"


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


def _ensure_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


def _local_now(now: datetime, tz_name: str) -> datetime:
    return _ensure_utc(now).astimezone(ZoneInfo(tz_name))


def subject_daily_slot_minute(subject_id: UUID, *, window_minutes: int) -> int:
    """Stable minute offset in [0, window_minutes) to spread load across tenants."""
    if window_minutes <= 1:
        return 0
    return int(subject_id.int % window_minutes)


def subject_daily_slot_at(
    subject_id: UUID,
    local_day: date,
    *,
    settings: Settings,
) -> datetime:
    """Local datetime when this subject becomes eligible on ``local_day``."""
    tz = ZoneInfo(SAMPLING_TIMEZONE)
    start = datetime(
        local_day.year,
        local_day.month,
        local_day.day,
        settings.sampling_daily_hour,
        0,
        0,
        tzinfo=tz,
    )
    offset = subject_daily_slot_minute(
        subject_id,
        window_minutes=settings.sampling_daily_window_minutes,
    )
    return start + timedelta(minutes=offset)


def last_sampled_local_date(subject: Subject) -> date | None:
    if subject.last_sampled_at is None:
        return None
    return _ensure_utc(subject.last_sampled_at).astimezone(ZoneInfo(SAMPLING_TIMEZONE)).date()


def is_subject_due_for_scheduled_sampling(
    subject: Subject,
    *,
    now: datetime | None = None,
    settings: Settings | None = None,
) -> bool:
    """True when local time passed today's slot and subject not yet sampled today."""
    settings = settings or get_settings()
    now = now or datetime.now(UTC)
    local_now = _local_now(now, SAMPLING_TIMEZONE)
    local_today = local_now.date()
    slot_at = subject_daily_slot_at(subject.id, local_today, settings=settings)
    if local_now < slot_at:
        return False
    last_day = last_sampled_local_date(subject)
    return last_day is None or last_day < local_today


def find_subjects_due_for_scheduled_sampling(
    db: Session,
    *,
    now: datetime | None = None,
    settings: Settings | None = None,
) -> list[Subject]:
    settings = settings or get_settings()
    now = now or datetime.now(UTC)
    subjects = list(db.execute(select(Subject)).scalars().all())
    due: list[Subject] = []
    for subject in subjects:
        if not is_subject_due_for_scheduled_sampling(subject, now=now, settings=settings):
            continue
        if subject_has_active_sampling_job(db, subject.id):
            continue
        if not subject_has_enabled_prompts(db, subject.id):
            continue
        due.append(subject)
    due.sort(
        key=lambda s: subject_daily_slot_minute(
            s.id,
            window_minutes=settings.sampling_daily_window_minutes,
        )
    )
    limit = settings.sampling_scheduler_max_enqueue_per_tick
    return due[:limit]
