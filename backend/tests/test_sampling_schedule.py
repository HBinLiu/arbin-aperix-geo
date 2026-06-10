"""Tests for scheduled sampling interval logic."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from aperix_geo.db.models import Subject, SubjectType
from aperix_geo.services.sampling.workflow import (
    ALLOWED_SAMPLING_INTERVAL_HOURS,
    is_subject_due_for_scheduled_sampling,
    validate_sampling_interval,
)


def test_validate_sampling_interval() -> None:
    assert validate_sampling_interval(24) == 24
    try:
        validate_sampling_interval(48)
        raise AssertionError("expected ValueError")
    except ValueError:
        pass
    assert ALLOWED_SAMPLING_INTERVAL_HOURS == frozenset({0, 6, 12, 24, 72, 168})


def test_is_subject_due_for_scheduled_sampling() -> None:
    now = datetime(2026, 5, 20, 12, 0, tzinfo=UTC)
    subject = Subject(
        id=uuid4(),
        tenant_id=uuid4(),
        type=SubjectType.domain,
        domain="example.com",
        sampling_interval=24,
        last_sampled_at=datetime(2026, 5, 19, 12, 0, tzinfo=UTC),
    )
    assert is_subject_due_for_scheduled_sampling(subject, now=now) is True

    subject.sampling_interval = 0
    assert is_subject_due_for_scheduled_sampling(subject, now=now) is False

    subject.sampling_interval = 24
    subject.last_sampled_at = now - timedelta(hours=1)
    assert is_subject_due_for_scheduled_sampling(subject, now=now) is False
