"""Tests for stale sampling job recovery."""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch
from uuid import uuid4

from aperix_geo.db.models import SamplingJob, SamplingJobStatus
from aperix_geo.services.sampling.workflow import (
    is_sampling_job_stale,
    reconcile_active_sampling_job,
    sampling_job_activity_at,
)


def _job(*, status: SamplingJobStatus, updated_at: datetime) -> SamplingJob:
    return SamplingJob(
        id=uuid4(),
        tenant_id=uuid4(),
        subject_id=uuid4(),
        status=status,
        total_items=2,
        created_at=updated_at - timedelta(minutes=5),
        started_at=updated_at - timedelta(minutes=4),
        updated_at=updated_at,
    )


def test_sampling_job_activity_at_prefers_updated_at() -> None:
    now = datetime(2026, 6, 2, 12, 0, tzinfo=UTC)
    job = _job(status=SamplingJobStatus.running, updated_at=now)
    assert sampling_job_activity_at(job) == now


def test_is_sampling_job_stale_when_inactive() -> None:
    now = datetime(2026, 6, 2, 12, 0, tzinfo=UTC)
    job = _job(status=SamplingJobStatus.running, updated_at=now - timedelta(seconds=120))
    assert is_sampling_job_stale(job, now=now, stale_seconds=90) is True


def test_is_sampling_job_not_stale_when_recent() -> None:
    now = datetime(2026, 6, 2, 12, 0, tzinfo=UTC)
    job = _job(status=SamplingJobStatus.running, updated_at=now - timedelta(seconds=30))
    assert is_sampling_job_stale(job, now=now, stale_seconds=90) is False


@patch("aperix_geo.services.sampling.workflow.recovery.finalize_sampling_job_db")
@patch("aperix_geo.services.sampling.workflow.recovery.pending_response_ids")
def test_reconcile_finalizes_when_no_pending(mock_pending_ids: MagicMock, mock_finalize: MagicMock) -> None:
    job = _job(status=SamplingJobStatus.running, updated_at=datetime.now(UTC))
    db = MagicMock()
    mock_pending_ids.return_value = []

    assert reconcile_active_sampling_job(db, job) is True
    mock_finalize.assert_called_once_with(db, job.id)
    mock_finalize.reset_mock()

    job.status = SamplingJobStatus.succeed
    assert reconcile_active_sampling_job(db, job) is False
    mock_finalize.assert_not_called()


@patch("aperix_geo.services.sampling.workflow.recovery.try_schedule_sampling_resume")
@patch("aperix_geo.services.sampling.workflow.recovery.pending_response_ids")
def test_reconcile_resumes_stale_job_with_pending(
    mock_pending_ids: MagicMock,
    mock_debounce: MagicMock,
) -> None:
    now = datetime(2026, 6, 2, 12, 0, tzinfo=UTC)
    job = _job(status=SamplingJobStatus.running, updated_at=now - timedelta(seconds=120))
    db = MagicMock()
    pending = [uuid4(), uuid4(), uuid4()]
    mock_pending_ids.return_value = pending
    mock_debounce.return_value = True
    mock_resume = MagicMock()

    with patch("aperix_geo.services.sampling.workflow.orchestrate.enqueue_sampling_resume", mock_resume):
        assert reconcile_active_sampling_job(db, job, now=now) is True

    mock_resume.assert_called_once_with(job.id, pending)


@patch("aperix_geo.services.sampling.workflow.recovery.try_schedule_sampling_resume")
@patch("aperix_geo.services.sampling.workflow.recovery.pending_response_ids")
def test_reconcile_skips_fresh_active_job(mock_pending_ids: MagicMock, mock_debounce: MagicMock) -> None:
    now = datetime(2026, 6, 2, 12, 0, tzinfo=UTC)
    job = _job(status=SamplingJobStatus.running, updated_at=now - timedelta(seconds=10))
    db = MagicMock()
    mock_pending_ids.return_value = [uuid4(), uuid4()]

    assert reconcile_active_sampling_job(db, job, now=now) is False
    mock_debounce.assert_not_called()


@patch("aperix_geo.services.sampling.workflow.recovery.try_schedule_sampling_resume")
@patch("aperix_geo.services.sampling.workflow.recovery.pending_response_ids")
def test_reconcile_force_resumes_without_stale_check(
    mock_pending_ids: MagicMock,
    mock_debounce: MagicMock,
) -> None:
    now = datetime(2026, 6, 2, 12, 0, tzinfo=UTC)
    job = _job(status=SamplingJobStatus.queued, updated_at=now - timedelta(seconds=5))
    db = MagicMock()
    pending = [uuid4()]
    mock_pending_ids.return_value = pending
    mock_debounce.return_value = True
    mock_resume = MagicMock()

    with patch("aperix_geo.services.sampling.workflow.orchestrate.enqueue_sampling_resume", mock_resume):
        assert reconcile_active_sampling_job(db, job, now=now, force=True) is True

    mock_resume.assert_called_once_with(job.id, pending)
