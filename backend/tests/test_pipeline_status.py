"""Tests for pipeline status helpers."""

from uuid import uuid4
from unittest.mock import MagicMock

from aperix_geo.db.models import SamplingJob, SamplingJobStatus
from aperix_geo.services.sampling.workflow.status import (
    _pipeline_stage_for_active_job,
    build_pipeline_status,
    is_pipeline_complete,
    should_close_pipeline_stream,
)


def test_active_job_stage_moves_to_clean_after_llm() -> None:
    assert _pipeline_stage_for_active_job(
        llm_pending_count=0,
        llm_ready_count=0,
        crawl_ready_count=3,
        response_count=10,
        parsed_count=10,
    ) == "clean"


def test_build_pipeline_status_uses_clean_while_parsing() -> None:
    from datetime import UTC, datetime

    job_id = uuid4()
    subject_id = uuid4()
    now = datetime.now(UTC)
    job = SamplingJob(
        id=job_id,
        subject_id=subject_id,
        tenant_id=uuid4(),
        status=SamplingJobStatus.running,
        total_items=10,
        created_at=now,
        started_at=now,
    )
    db = MagicMock()
    db.get.return_value = job

    counts_result = MagicMock()
    counts_result.one.return_value = (0, 0, 2, 8, 8)
    db.execute.return_value = counts_result

    from aperix_geo.services.sampling.workflow import status as status_mod

    original = status_mod.get_latest_sampling_job
    status_mod.get_latest_sampling_job = lambda _db, _sid: job
    try:
        payload = build_pipeline_status(db, subject_id=subject_id)
    finally:
        status_mod.get_latest_sampling_job = original

    assert payload["stage"] == "clean"
    assert payload["worker_phase"] == "parse"


def test_is_pipeline_complete_requires_parsed_responses() -> None:
    status = {
        "latest_job": {"status": "succeed"},
        "response_count": 10,
        "parsed_count": 10,
    }
    assert is_pipeline_complete(status) is True

    partial = {**status, "parsed_count": 3}
    assert is_pipeline_complete(partial) is False


def test_should_close_on_terminal_failure_without_responses() -> None:
    status = {
        "latest_job": {"status": "failed"},
        "response_count": 0,
        "parsed_count": 0,
    }
    assert should_close_pipeline_stream(status) is True
