"""Tests for daily scheduled sampling logic."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from aperix_geo.config import Settings
from aperix_geo.db.models import Subject, SubjectType
from aperix_geo.services.sampling.workflow.schedule import (
    is_subject_due_for_scheduled_sampling,
    subject_daily_slot_at,
    subject_daily_slot_minute,
)


def _settings(**overrides) -> Settings:
    base = {
        "sampling_daily_hour": 2,
        "sampling_daily_window_minutes": 120,
        "sampling_scheduler_max_enqueue_per_tick": 50,
    }
    base.update(overrides)
    return Settings(**base)


def test_subject_daily_slot_minute_stable() -> None:
    subject_id = uuid4()
    assert subject_daily_slot_minute(subject_id, window_minutes=120) == subject_daily_slot_minute(
        subject_id,
        window_minutes=120,
    )
    assert 0 <= subject_daily_slot_minute(subject_id, window_minutes=120) < 120


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
