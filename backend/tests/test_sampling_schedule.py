"""Tests for daily scheduled sampling logic."""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock
from uuid import uuid4
from zoneinfo import ZoneInfo

from aperix_geo.config import Settings
from aperix_geo.db.models import Subject, SubjectType
from aperix_geo.services.sampling.workflow.schedule import (
    find_subjects_due_for_scheduled_sampling,
    is_subject_due_for_scheduled_sampling,
    is_within_sampling_enqueue_window,
    sampling_beat_cron_hour_range,
    sampling_window_end,
    sampling_window_start,
    subject_daily_slot_at,
    subject_daily_slot_minute,
    subject_has_active_sampling_job,
)


def _settings(**overrides) -> Settings:
    base = {
        "sampling_daily_hour": 2,
        "sampling_daily_window_minutes": 180,
        "sampling_scheduler_max_enqueue_per_run": 50,
    }
    base.update(overrides)
    return Settings(**base)


def test_subject_daily_slot_minute_stable() -> None:
    subject_id = uuid4()
    assert subject_daily_slot_minute(subject_id, window_minutes=180) == subject_daily_slot_minute(
        subject_id,
        window_minutes=180,
    )
    assert 0 <= subject_daily_slot_minute(subject_id, window_minutes=180) < 180


def test_sampling_window_is_two_to_five_beijing() -> None:
    settings = _settings()
    local_day = datetime(2026, 5, 20).date()
    tz = ZoneInfo("Asia/Shanghai")
    start = sampling_window_start(local_day, settings=settings)
    end = sampling_window_end(local_day, settings=settings)
    assert start == datetime(2026, 5, 20, 2, 0, tzinfo=tz)
    assert end == datetime(2026, 5, 20, 5, 0, tzinfo=tz)
    assert sampling_beat_cron_hour_range(settings=settings) == "2-4"
    inside = datetime(2026, 5, 20, 4, 30, tzinfo=tz)
    outside = datetime(2026, 5, 20, 10, 0, tzinfo=tz)
    assert is_within_sampling_enqueue_window(inside, settings=settings) is True
    assert is_within_sampling_enqueue_window(outside, settings=settings) is False


def test_is_subject_due_after_slot_and_not_sampled_today() -> None:
    settings = _settings()
    subject_id = uuid4()
    slot = subject_daily_slot_at(subject_id, datetime(2026, 5, 20).date(), settings=settings)
    subject = Subject(
        id=subject_id,
        tenant_id=uuid4(),
        type=SubjectType.domain,
        domain="example.com",
        last_sampled_at=datetime(2026, 5, 19, 10, 0, tzinfo=UTC),
    )
    assert is_subject_due_for_scheduled_sampling(
        subject,
        now=slot.astimezone(UTC),
        settings=settings,
    ) is True


def test_is_subject_not_due_before_daily_window() -> None:
    settings = _settings()
    subject_id = uuid4()
    subject = Subject(
        id=subject_id,
        tenant_id=uuid4(),
        type=SubjectType.domain,
        domain="example.com",
        last_sampled_at=datetime(2026, 5, 19, 10, 0, tzinfo=UTC),
    )
    # 2026-05-20 01:30 CST = still before 02:00 window
    before = datetime(2026, 5, 19, 17, 30, tzinfo=UTC)
    assert is_subject_due_for_scheduled_sampling(subject, now=before, settings=settings) is False


def test_is_subject_not_due_when_already_sampled_today() -> None:
    settings = _settings()
    subject_id = uuid4()
    slot = subject_daily_slot_at(subject_id, datetime(2026, 5, 20).date(), settings=settings)
    subject = Subject(
        id=subject_id,
        tenant_id=uuid4(),
        type=SubjectType.domain,
        domain="example.com",
        last_sampled_at=slot.astimezone(UTC),
    )
    later = slot.astimezone(UTC) + timedelta(hours=1)
    assert is_subject_due_for_scheduled_sampling(subject, now=later, settings=settings) is False


def test_is_subject_not_due_outside_enqueue_window_even_if_slot_passed() -> None:
    settings = _settings()
    subject_id = uuid4()
    slot = subject_daily_slot_at(subject_id, datetime(2026, 5, 20).date(), settings=settings)
    subject = Subject(
        id=subject_id,
        tenant_id=uuid4(),
        type=SubjectType.domain,
        domain="example.com",
        last_sampled_at=datetime(2026, 5, 19, 10, 0, tzinfo=UTC),
    )
    afternoon_cst = datetime(2026, 5, 20, 10, 0, tzinfo=ZoneInfo("Asia/Shanghai"))
    assert slot < afternoon_cst
    assert is_subject_due_for_scheduled_sampling(
        subject,
        now=afternoon_cst.astimezone(UTC),
        settings=settings,
    ) is False


def test_find_subjects_due_skips_db_outside_window() -> None:
    db = MagicMock()
    settings = _settings()
    outside = datetime(2026, 5, 20, 10, 0, tzinfo=ZoneInfo("Asia/Shanghai")).astimezone(UTC)

    assert find_subjects_due_for_scheduled_sampling(db, now=outside, settings=settings) == []

    db.execute.assert_not_called()


def test_find_subjects_due_uses_single_subject_query() -> None:
    settings = _settings()
    subject_id = uuid4()
    slot = subject_daily_slot_at(subject_id, datetime(2026, 5, 20).date(), settings=settings)
    subject = Subject(
        id=subject_id,
        tenant_id=uuid4(),
        type=SubjectType.domain,
        domain="example.com",
        last_sampled_at=datetime(2026, 5, 19, 10, 0, tzinfo=UTC),
    )
    db = MagicMock()
    db.execute.return_value.scalars.return_value.all.return_value = [subject]

    due = find_subjects_due_for_scheduled_sampling(
        db,
        now=slot.astimezone(UTC),
        settings=settings,
    )

    assert due == [subject]
    db.execute.assert_called_once()


def test_subject_has_active_sampling_job_uses_scalar() -> None:
    db = MagicMock()
    db.scalar.return_value = True
    subject_id = uuid4()

    assert subject_has_active_sampling_job(db, subject_id) is True

    db.scalar.assert_called_once()
