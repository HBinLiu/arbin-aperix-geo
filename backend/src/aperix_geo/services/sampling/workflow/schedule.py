"""Scheduled sampling: daily window + per-subject slot within window."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import desc, exists, select
from sqlalchemy.orm import Session, aliased

from aperix_geo.config import Settings, get_settings
from aperix_geo.db.models import Prompt, SamplingJob, SamplingJobStatus, Subject
from aperix_geo.services.sampling.frequency import sampling_interval_days
from aperix_geo.utils.datetime import ensure_utc

# 固定北京时间；「今日是否已采样」与每日窗口均按此计算
SAMPLING_TIMEZONE = "Asia/Shanghai"


def sampling_beat_cron_hour_range(*, settings: Settings | None = None) -> str:
    """Inclusive local-hour range for Celery Beat crontab (e.g. ``2-4`` for 02:00–04:59)."""
    settings = settings or get_settings()
    start = settings.sampling_daily_hour
    end_inclusive = start + (settings.sampling_daily_window_minutes - 1) // 60
    if end_inclusive <= start:
        return str(start)
    return f"{start}-{end_inclusive}"


def get_latest_sampling_job(db: Session, subject_id: UUID) -> SamplingJob | None:
    return db.execute(
        select(SamplingJob)
        .where(SamplingJob.subject_id == subject_id)
        .order_by(desc(SamplingJob.created_at))
        .limit(1)
    ).scalar_one_or_none()


def _latest_active_sampling_job_exists(subject_id_col) -> exists:
    """Correlated EXISTS: the subject's newest sampling job is queued or running."""
    job = aliased(SamplingJob)
    newer_job = aliased(SamplingJob)
    return exists(
        select(1)
        .select_from(job)
        .where(
            job.subject_id == subject_id_col,
            job.status.in_((SamplingJobStatus.queued, SamplingJobStatus.running)),
            ~exists(
                select(1)
                .select_from(newer_job)
                .where(
                    newer_job.subject_id == job.subject_id,
                    newer_job.created_at > job.created_at,
                )
            ),
        )
    )


def _has_enabled_prompt_exists(subject_id_col) -> exists:
    return exists(
        select(Prompt.id).where(
            Prompt.subject_id == subject_id_col,
            Prompt.enabled.is_(True),
        )
    )


def subject_has_active_sampling_job(db: Session, subject_id: UUID) -> bool:
    return bool(
        db.scalar(
            select(_latest_active_sampling_job_exists(subject_id)),
        )
    )


def _local_now(now: datetime, tz_name: str) -> datetime:
    return ensure_utc(now).astimezone(ZoneInfo(tz_name))


def sampling_window_start(local_day: date, *, settings: Settings) -> datetime:
    """Local datetime when the daily enqueue window opens."""
    tz = ZoneInfo(SAMPLING_TIMEZONE)
    return datetime(
        local_day.year,
        local_day.month,
        local_day.day,
        settings.sampling_daily_hour,
        0,
        0,
        tzinfo=tz,
    )


def sampling_window_end(local_day: date, *, settings: Settings) -> datetime:
    """Local datetime when the daily enqueue window closes (exclusive)."""
    return sampling_window_start(local_day, settings=settings) + timedelta(
        minutes=settings.sampling_daily_window_minutes,
    )


def is_within_sampling_enqueue_window(
    local_now: datetime,
    *,
    settings: Settings,
) -> bool:
    """True when scheduled sampling jobs may be enqueued (Beijing local time)."""
    start = sampling_window_start(local_now.date(), settings=settings)
    end = sampling_window_end(local_now.date(), settings=settings)
    return start <= local_now < end


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
    start = sampling_window_start(local_day, settings=settings)
    offset = subject_daily_slot_minute(
        subject_id,
        window_minutes=settings.sampling_daily_window_minutes,
    )
    return start + timedelta(minutes=offset)


def last_sampled_local_date(subject: Subject) -> date | None:
    if subject.last_sampled_at is None:
        return None
    return ensure_utc(subject.last_sampled_at).astimezone(ZoneInfo(SAMPLING_TIMEZONE)).date()


def is_subject_past_daily_slot(
    subject: Subject,
    *,
    now: datetime | None = None,
    settings: Settings | None = None,
) -> bool:
    """True when local time is past this subject's slot on today's window day."""
    settings = settings or get_settings()
    now = now or datetime.now(UTC)
    local_now = _local_now(now, SAMPLING_TIMEZONE)
    slot_at = subject_daily_slot_at(subject.id, local_now.date(), settings=settings)
    return local_now >= slot_at


def is_subject_due_for_scheduled_sampling(
    subject: Subject,
    *,
    now: datetime | None = None,
    settings: Settings | None = None,
) -> bool:
    """True when local time is inside today's window, past slot, and interval elapsed."""
    settings = settings or get_settings()
    now = now or datetime.now(UTC)
    local_now = _local_now(now, SAMPLING_TIMEZONE)
    if not is_within_sampling_enqueue_window(local_now, settings=settings):
        return False
    local_today = local_now.date()
    slot_at = subject_daily_slot_at(subject.id, local_today, settings=settings)
    if local_now < slot_at:
        return False
    last_day = last_sampled_local_date(subject)
    if last_day is None:
        return True
    interval_days = sampling_interval_days(subject.sampling_frequency)
    return (local_today - last_day).days >= interval_days


def find_subjects_due_for_scheduled_sampling(
    db: Session,
    *,
    now: datetime | None = None,
    settings: Settings | None = None,
) -> list[Subject]:
    settings = settings or get_settings()
    now = now or datetime.now(UTC)
    local_now = _local_now(now, SAMPLING_TIMEZONE)
    if not is_within_sampling_enqueue_window(local_now, settings=settings):
        return []

    stmt = (
        select(Subject)
        .where(Subject.deleted.is_(False))
        .where(_has_enabled_prompt_exists(Subject.id))
        .where(~_latest_active_sampling_job_exists(Subject.id))
    )
    candidates = list(db.execute(stmt).scalars().all())
    due = [
        subject
        for subject in candidates
        if is_subject_due_for_scheduled_sampling(subject, now=now, settings=settings)
    ]
    due.sort(
        key=lambda s: subject_daily_slot_minute(
            s.id,
            window_minutes=settings.sampling_daily_window_minutes,
        )
    )
    limit = settings.sampling_scheduler_max_enqueue_per_run
    return due[:limit]


_SCHEDULE_ANCHOR_PREFIX = "aperix:sampling:schedule_anchor:"


def remember_schedule_anchor_for_job(job_id: UUID, *, subject_id: UUID) -> None:
    """Defer last_sampled_at update until the job finishes successfully."""
    from aperix_geo.utils.cache.redis_kv import redis_set_json_exat
    from aperix_geo.utils.cache.ttl import expires_at_from_ttl

    ttl_s = max(3600, get_settings().sampling_stale_job_seconds * 40)
    expires_at = expires_at_from_ttl(ttl_s)
    redis_set_json_exat(
        f"{_SCHEDULE_ANCHOR_PREFIX}{job_id}",
        {"subject_id": str(subject_id), "expires_at": expires_at},
        expires_at=expires_at,
    )


def commit_schedule_anchor_if_due(db: Session, job: SamplingJob) -> None:
    """Apply deferred last_sampled_at when a scheduled job reaches a successful terminal state."""
    from aperix_geo.utils.cache.redis_kv import redis_delete, redis_get_json

    key = f"{_SCHEDULE_ANCHOR_PREFIX}{job.id}"
    if job.status in (SamplingJobStatus.succeed, SamplingJobStatus.partial):
        payload = redis_get_json(key)
        if not payload:
            return
        subject_id_raw = payload.get("subject_id")
        if subject_id_raw:
            subject = db.get(Subject, UUID(str(subject_id_raw)))
            if subject is not None:
                subject.last_sampled_at = datetime.now(UTC)
        redis_delete(key)
        return

    if job.status == SamplingJobStatus.failed:
        redis_delete(key)
