"""Tests for sampling pipeline status (read-only)."""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch
from uuid import uuid4

from aperix_geo.db.models import SamplingJob, SamplingJobStatus
from aperix_geo.services.sampling.workflow.status import build_pipeline_status


@patch("aperix_geo.services.sampling.workflow.status.get_latest_sampling_job")
def test_build_pipeline_status_does_not_trigger_recovery(
    mock_latest_job: MagicMock,
) -> None:
    subject_id = uuid4()
    job = SamplingJob(
        id=uuid4(),
        tenant_id=uuid4(),
        subject_id=subject_id,
        status=SamplingJobStatus.running,
        total_items=2,
        created_at=datetime.now(UTC),
    )
    mock_latest_job.return_value = job
    db = MagicMock()

    with patch(
        "aperix_geo.services.sampling.workflow.status._response_counts_for_job",
        return_value={
            "llm_pending_count": 1,
            "llm_ready_count": 0,
            "crawl_ready_count": 0,
            "response_count": 0,
            "parsed_count": 0,
        },
    ):
        result = build_pipeline_status(db, subject_id=subject_id)

    assert result["phase"] == "llm"
    assert result["latest_job"]["id"] == str(job.id)
