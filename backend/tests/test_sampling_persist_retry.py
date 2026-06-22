"""Tests for shared persist retry helper."""

from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import uuid4

from sqlalchemy.exc import DBAPIError

from aperix_geo.services.sampling.workflow.persist_retry import run_persist_with_db_retry


@patch("aperix_geo.services.sampling.workflow.persist_retry.defer_sampling_persist")
def test_run_persist_returns_success_when_persist_ok(mock_defer: MagicMock) -> None:
    task = MagicMock()
    task.request.retries = 0
    db = MagicMock()

    out = run_persist_with_db_retry(
        task,
        db,
        sampling_job_id=uuid4(),
        phase="llm",
        persist=lambda: True,
        on_skipped=lambda: {"ok": True, "skipped": True},
        on_success=lambda: {"ok": True, "phase": "llm"},
        fail=lambda: {"ok": False},
    )

    assert out == {"ok": True, "phase": "llm"}
    mock_defer.assert_not_called()


@patch("aperix_geo.services.sampling.workflow.persist_retry.defer_sampling_persist", return_value={"deferred": True})
@patch("aperix_geo.services.sampling.workflow.persist_retry.is_retryable_db_error", return_value=True)
@patch("aperix_geo.services.sampling.workflow.persist_retry.retry_if_transient")
def test_run_persist_defers_on_retryable_db_error(
    mock_retry: MagicMock,
    _mock_retryable: MagicMock,
    mock_defer: MagicMock,
) -> None:
    task = MagicMock()
    task.request.retries = 0
    db = MagicMock()
    job_id = uuid4()

    with patch("aperix_geo.services.sampling.workflow.persist_retry.get_settings") as mock_settings:
        mock_settings.return_value.sampling_db_retry_max = 1
        out = run_persist_with_db_retry(
            task,
            db,
            sampling_job_id=job_id,
            phase="parse",
            persist=lambda: (_ for _ in ()).throw(DBAPIError("stmt", {}, Exception("deadlock"))),
            on_skipped=lambda: {"ok": True, "skipped": True},
            fail=lambda: {"ok": False},
        )

    assert out == {"deferred": True}
    mock_defer.assert_called_once_with(
        sampling_job_id=job_id,
        error=mock_defer.call_args.kwargs["error"],
        phase="parse",
    )
    mock_retry.assert_called_once()
