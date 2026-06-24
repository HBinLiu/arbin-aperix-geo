"""Tests for stale sampling job recovery."""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch
from uuid import uuid4

from aperix_geo.db.models import SamplingJob, SamplingJobStatus
from aperix_geo.services.sampling.workflow.queues import ResponseWorkQueues
from aperix_geo.services.sampling.workflow.dispatch import try_schedule_sampling_job_enqueue
from aperix_geo.services.sampling.workflow.recovery import (
    is_sampling_job_stale,
    recover_active_sampling_job,
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
@patch("aperix_geo.services.sampling.workflow.recovery.response_work_queues")
def test_reconcile_finalizes_when_no_pending(
    mock_queues: MagicMock,
    mock_finalize: MagicMock,
) -> None:
    job = _job(status=SamplingJobStatus.running, updated_at=datetime.now(UTC))
    db = MagicMock()
    mock_queues.return_value = ResponseWorkQueues(pending=(), llm_ready=(), crawl_ready=())

    assert recover_active_sampling_job(db, job) is True
    mock_finalize.assert_called_once_with(db, job.id)
    mock_finalize.reset_mock()

    job.status = SamplingJobStatus.succeed
    assert recover_active_sampling_job(db, job) is False
    mock_finalize.assert_not_called()


@patch("aperix_geo.services.sampling.workflow.dispatch.try_schedule_sampling_job_enqueue")
@patch("aperix_geo.services.sampling.workflow.recovery.response_work_queues")
def test_reconcile_resumes_stale_job_with_pending(
    mock_queues: MagicMock,
    mock_debounce: MagicMock,
) -> None:
    now = datetime(2026, 6, 2, 12, 0, tzinfo=UTC)
    job = _job(status=SamplingJobStatus.running, updated_at=now - timedelta(seconds=120))
    db = MagicMock()
    pending = (uuid4(), uuid4(), uuid4())
    mock_queues.return_value = ResponseWorkQueues(pending=pending, llm_ready=(), crawl_ready=())
    mock_debounce.return_value = True
    mock_resume = MagicMock()
    mock_reset_inflight = MagicMock()
    mock_reset_dispatch = MagicMock()

    with (
        patch(
            "aperix_geo.services.sampling.workflow.fill.reset_all_inflight_slots",
            mock_reset_inflight,
        ),
        patch(
            "aperix_geo.services.sampling.workflow.fill.reset_all_dispatch_markers",
            mock_reset_dispatch,
        ),
        patch("aperix_geo.services.sampling.workflow.orchestrate.enqueue_sampling_continue", mock_resume),
    ):
        assert recover_active_sampling_job(db, job, now=now) is True

    mock_reset_inflight.assert_called_once_with(job.id)
    mock_reset_dispatch.assert_called_once_with(job.id)
    mock_resume.assert_called_once_with(job.id)


@patch("aperix_geo.services.sampling.workflow.dispatch.try_schedule_sampling_job_enqueue")
@patch("aperix_geo.services.sampling.workflow.recovery.response_work_queues")
def test_reconcile_skips_fresh_active_job(mock_queues: MagicMock, mock_debounce: MagicMock) -> None:
    now = datetime(2026, 6, 2, 12, 0, tzinfo=UTC)
    job = _job(status=SamplingJobStatus.running, updated_at=now - timedelta(seconds=10))
    db = MagicMock()
    mock_queues.return_value = ResponseWorkQueues(pending=(uuid4(), uuid4()), llm_ready=(), crawl_ready=())

    assert recover_active_sampling_job(db, job, now=now) is False
    mock_debounce.assert_not_called()


@patch("aperix_geo.services.sampling.workflow.dispatch.try_schedule_sampling_job_enqueue")
@patch("aperix_geo.services.sampling.workflow.recovery.response_work_queues")
def test_reconcile_force_resumes_without_stale_check(
    mock_queues: MagicMock,
    mock_debounce: MagicMock,
) -> None:
    now = datetime(2026, 6, 2, 12, 0, tzinfo=UTC)
    job = _job(status=SamplingJobStatus.queued, updated_at=now - timedelta(seconds=5))
    db = MagicMock()
    pending = (uuid4(),)
    mock_queues.return_value = ResponseWorkQueues(pending=pending, llm_ready=(), crawl_ready=())
    mock_debounce.return_value = True
    mock_resume = MagicMock()
    mock_reset_inflight = MagicMock()
    mock_reset_dispatch = MagicMock()

    with (
        patch(
            "aperix_geo.services.sampling.workflow.fill.reset_all_inflight_slots",
            mock_reset_inflight,
        ),
        patch(
            "aperix_geo.services.sampling.workflow.fill.reset_all_dispatch_markers",
            mock_reset_dispatch,
        ),
        patch("aperix_geo.services.sampling.workflow.orchestrate.enqueue_sampling_continue", mock_resume),
    ):
        assert recover_active_sampling_job(db, job, now=now, force=True) is True

    mock_reset_inflight.assert_not_called()
    mock_reset_dispatch.assert_not_called()
    mock_resume.assert_called_once_with(job.id)


@patch("aperix_geo.services.sampling.workflow.dispatch.redis_set_nx_strict", return_value=False)
@patch("aperix_geo.services.sampling.workflow.recovery.response_work_queues")
def test_reconcile_force_bypasses_resume_debounce(
    mock_queues: MagicMock,
    mock_set_nx: MagicMock,
) -> None:
    now = datetime(2026, 6, 2, 12, 0, tzinfo=UTC)
    job = _job(status=SamplingJobStatus.running, updated_at=now - timedelta(seconds=5))
    db = MagicMock()
    pending = (uuid4(),)
    mock_queues.return_value = ResponseWorkQueues(pending=pending, llm_ready=(), crawl_ready=())
    mock_resume = MagicMock()

    with patch("aperix_geo.services.sampling.workflow.orchestrate.enqueue_sampling_continue", mock_resume):
        assert recover_active_sampling_job(db, job, now=now, force=True) is True

    mock_set_nx.assert_not_called()
    mock_resume.assert_called_once_with(job.id)


@patch("aperix_geo.services.sampling.workflow.dispatch.redis_set_nx_strict", return_value=False)
def test_try_schedule_sampling_job_enqueue_force_skips_debounce(mock_set_nx: MagicMock) -> None:
    job_id = uuid4()
    assert try_schedule_sampling_job_enqueue(job_id, force=True) is True
    mock_set_nx.assert_not_called()
    assert try_schedule_sampling_job_enqueue(job_id, force=False) is False
    mock_set_nx.assert_called_once()
