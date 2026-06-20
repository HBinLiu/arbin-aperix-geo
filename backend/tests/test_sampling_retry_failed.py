"""Tests for retrying failed sampling responses within a job."""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from aperix_geo.db.models import LLMResponseStatus, SamplingJob, SamplingJobStatus
from aperix_geo.services.sampling.workflow.jobs import SamplingJobError
from aperix_geo.services.sampling.workflow.retry_failed import retry_failed_responses_for_job


def _job() -> SamplingJob:
    now = datetime.now(UTC)
    return SamplingJob(
        id=uuid4(),
        tenant_id=uuid4(),
        subject_id=uuid4(),
        status=SamplingJobStatus.partial,
        total_items=2,
        completed_items=1,
        failed_items=1,
        created_at=now,
        started_at=now,
        finished_at=now,
    )


@patch("aperix_geo.services.sampling.workflow.retry_failed.enqueue_sampling_resume")
@patch("aperix_geo.services.sampling.workflow.retry_failed.failed_response_ids")
def test_retry_failed_responses_resets_rows_and_dispatches(
    mock_failed_ids: MagicMock,
    mock_enqueue: MagicMock,
) -> None:
    job = _job()
    failed = [uuid4(), uuid4()]
    mock_failed_ids.return_value = failed

    db = MagicMock()
    db.get.return_value = job

    count = retry_failed_responses_for_job(db, job.id)

    assert count == 2
    db.execute.assert_called_once()
    assert job.status == SamplingJobStatus.running
    assert job.finished_at is None
    assert job.error_message == ""
    db.commit.assert_called_once()
    db.refresh.assert_called_once_with(job)
    mock_enqueue.assert_called_once_with(job.id, failed)


def test_retry_failed_responses_requires_failed_rows() -> None:
    job = _job()
    db = MagicMock()
    db.get.return_value = job

    with patch(
        "aperix_geo.services.sampling.workflow.retry_failed.failed_response_ids",
        return_value=[],
    ):
        with pytest.raises(SamplingJobError, match="No failed responses"):
            retry_failed_responses_for_job(db, job.id)


def test_retry_failed_responses_requires_existing_job() -> None:
    db = MagicMock()
    db.get.return_value = None

    with pytest.raises(SamplingJobError, match="not found"):
        retry_failed_responses_for_job(db, uuid4())
