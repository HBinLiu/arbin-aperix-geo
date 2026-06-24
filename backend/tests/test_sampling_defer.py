"""Tests for deferred persist recovery on transient DB errors."""

from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import uuid4

from aperix_geo.services.sampling.workflow.defer import defer_sampling_persist
from aperix_geo.services.sampling.workflow.phase_specs import _fail_pending


@patch("aperix_geo.services.sampling.workflow.orchestrate.enqueue_sampling_continue")
@patch("aperix_geo.services.sampling.workflow.dispatch.try_schedule_sampling_job_enqueue", return_value=True)
def test_defer_persist_schedules_continue(mock_debounce: MagicMock, mock_continue: MagicMock) -> None:
    job_id = uuid4()

    out = defer_sampling_persist(
        sampling_job_id=job_id,
        error="deadlock",
        phase="llm",
    )

    assert out["deferred"] is True
    assert out["ok"] is False
    assert out["phase"] == "llm"
    mock_debounce.assert_called_once_with(job_id)
    mock_continue.assert_called_once_with(job_id)


@patch("aperix_geo.services.sampling.workflow.phase_specs.clear_cached_llm_result")
@patch("aperix_geo.services.sampling.workflow.phase_specs.mark_response_failed_if_pending")
def test_fail_pending_clears_cache_and_marks_failed(
    mock_mark: MagicMock,
    mock_clear: MagicMock,
) -> None:
    db = MagicMock()
    response_id = uuid4()

    out = _fail_pending(db, response_id=response_id, error="bad data")

    assert out["ok"] is False
    assert "deferred" not in out
    mock_mark.assert_called_once()
    mock_clear.assert_called_once_with(response_id)
