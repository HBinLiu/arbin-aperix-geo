"""Tests for sampling finalize task."""

from unittest.mock import MagicMock, patch


@patch("aperix_geo.tasks.sampling.SessionLocal")
@patch("aperix_geo.services.sampling.workflow.finalize.finalize_sampling_job_db")
def test_sampling_finalize_skips_empty_job_id(
    mock_finalize: MagicMock,
    mock_session_local: MagicMock,
) -> None:
    from aperix_geo.tasks.sampling import sampling_finalize

    sampling_finalize("")
    mock_session_local.assert_not_called()
    mock_finalize.assert_not_called()


@patch("aperix_geo.tasks.sampling._run_sampling_finalize")
def test_sampling_reconcile_legacy_forwards(mock_run: MagicMock) -> None:
    from aperix_geo.tasks.sampling import sampling_reconcile_legacy

    sampling_reconcile_legacy("job-1")
    mock_run.assert_called_once_with("job-1")
