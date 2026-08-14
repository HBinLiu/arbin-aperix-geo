"""Tests for sampling phase fill dispatch."""

from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import uuid4


@patch("aperix_geo.services.sampling.workflow.fill.schedule_job_finalize")
@patch("aperix_geo.services.sampling.workflow.fill.fill_phase")
def test_dispatch_phases_fills_all_phases(mock_fill: MagicMock, mock_reconcile: MagicMock) -> None:
    from aperix_geo.services.sampling.workflow.fill import dispatch_phases

    job_id = str(uuid4())
    mock_fill.side_effect = [3, 0, 2]

    assert dispatch_phases(job_id) is True
    assert mock_fill.call_count == 3
    mock_reconcile.assert_not_called()


@patch("aperix_geo.services.sampling.workflow.fill.schedule_job_finalize")
@patch("aperix_geo.services.sampling.workflow.fill.fill_phase", return_value=0)
def test_dispatch_phases_reconciles_when_idle(mock_fill: MagicMock, mock_reconcile: MagicMock) -> None:
    from aperix_geo.services.sampling.workflow.fill import dispatch_phases

    job_id = str(uuid4())
    assert dispatch_phases(job_id) is False
    assert mock_fill.call_count == 3
    mock_reconcile.assert_called_once()


@patch("aperix_geo.services.sampling.workflow.fill.schedule_job_finalize")
@patch("aperix_geo.services.sampling.workflow.fill.schedule_phase_fill")
@patch("aperix_geo.services.sampling.workflow.fill.release_inflight_slot")
@patch("aperix_geo.services.sampling.workflow.fill.release_response_dispatched")
@patch("aperix_geo.services.sampling.workflow.fill.SessionLocal")
def test_on_task_finished_releases_and_refills(
    mock_session_local: MagicMock,
    mock_release_dispatch: MagicMock,
    mock_release: MagicMock,
    mock_schedule_fill: MagicMock,
    mock_reconcile: MagicMock,
) -> None:
    from aperix_geo.services.sampling.workflow.fill import on_task_finished

    response_id = uuid4()
    job_id = uuid4()
    mock_release_dispatch.return_value = (job_id, "")

    on_task_finished(response_id, "llm")

    mock_release_dispatch.assert_called_once_with("llm", response_id)
    mock_release.assert_called_once_with(job_id, "llm", lane="")
    assert mock_schedule_fill.call_count == 2
    mock_schedule_fill.assert_any_call(str(job_id), "llm")
    mock_schedule_fill.assert_any_call(str(job_id), "page")
    mock_reconcile.assert_called_once_with(job_id)
    mock_session_local.assert_not_called()


@patch("aperix_geo.services.sampling.workflow.fill.release_inflight_slot")
@patch("aperix_geo.services.sampling.workflow.fill.schedule_phase_fill")
@patch("aperix_geo.services.sampling.workflow.fill.schedule_job_finalize")
def test_on_task_claim_lost_only_releases_inflight(
    mock_reconcile: MagicMock,
    mock_schedule_fill: MagicMock,
    mock_release: MagicMock,
) -> None:
    from aperix_geo.services.sampling.workflow.fill import on_task_claim_lost

    response_id = uuid4()
    job_id = uuid4()

    on_task_claim_lost(response_id, "parse", job_id=job_id)

    mock_release.assert_called_once_with(job_id, "parse")
    mock_schedule_fill.assert_not_called()
    mock_reconcile.assert_not_called()


@patch("aperix_geo.services.sampling.workflow.fill._send_phase_task")
@patch(
    "aperix_geo.services.sampling.workflow.fill.try_mark_response_dispatched",
    side_effect=[True, False, True, False, False],
)
@patch("aperix_geo.services.sampling.workflow.fill.reclaim_stale_response_dispatch")
@patch("aperix_geo.services.sampling.workflow.fill.release_response_dispatched")
@patch("aperix_geo.services.sampling.workflow.fill.try_reserve_inflight_slot", return_value=True)
@patch("aperix_geo.services.sampling.workflow.fill.SessionLocal")
def test_fill_phase_dispatches_until_cap_or_empty(
    mock_session_local: MagicMock,
    mock_reserve: MagicMock,
    _mock_release_dispatch: MagicMock,
    _mock_reclaim: MagicMock,
    mock_mark: MagicMock,
    mock_send: MagicMock,
) -> None:
    from aperix_geo.services.sampling.workflow.fill import fill_phase

    job_id = str(uuid4())
    rows = []
    for _ in range(2):
        row = MagicMock()
        row.id = uuid4()
        row.platform = "deepseek"
        rows.append(row)
    db = MagicMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = rows
    db.execute.return_value = result
    mock_session_local.return_value = db

    count = fill_phase(job_id, "llm")

    assert count == 2
    assert mock_send.call_count == 2
    mock_reserve.assert_called()


@patch("aperix_geo.services.sampling.workflow.fill._send_phase_task")
@patch("aperix_geo.services.sampling.workflow.fill.try_mark_response_dispatched", return_value=True)
@patch("aperix_geo.services.sampling.workflow.fill.reclaim_stale_response_dispatch")
@patch("aperix_geo.services.sampling.workflow.fill.release_response_dispatched")
@patch("aperix_geo.services.sampling.workflow.fill.try_reserve_inflight_slot", return_value=False)
@patch("aperix_geo.services.sampling.workflow.fill.SessionLocal")
def test_fill_phase_releases_mark_when_inflight_cap_hit(
    mock_session_local: MagicMock,
    mock_reserve: MagicMock,
    mock_release_dispatch: MagicMock,
    _mock_reclaim: MagicMock,
    _mock_mark: MagicMock,
    mock_send: MagicMock,
) -> None:
    from aperix_geo.services.sampling.workflow.fill import fill_phase

    job_id = str(uuid4())
    row = MagicMock()
    row.id = uuid4()
    row.platform = "deepseek"
    db = MagicMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = [row]
    db.execute.return_value = result
    mock_session_local.return_value = db

    count = fill_phase(job_id, "llm")

    assert count == 0
    mock_send.assert_not_called()
    mock_release_dispatch.assert_called_once()


@patch("aperix_geo.services.sampling.workflow.fill._send_phase_task")
@patch("aperix_geo.services.sampling.workflow.fill.try_mark_response_dispatched", return_value=False)
@patch("aperix_geo.services.sampling.workflow.fill.release_inflight_slot")
@patch("aperix_geo.services.sampling.workflow.fill.try_reserve_inflight_slot", return_value=True)
@patch("aperix_geo.services.sampling.workflow.fill.SessionLocal")
def test_fill_phase_skips_when_all_candidates_already_dispatched(
    mock_session_local: MagicMock,
    mock_reserve: MagicMock,
    mock_release: MagicMock,
    _mock_mark: MagicMock,
    mock_send: MagicMock,
) -> None:
    from aperix_geo.services.sampling.workflow.fill import fill_phase

    job_id = str(uuid4())
    row = MagicMock()
    row.id = uuid4()
    row.platform = "deepseek"
    db = MagicMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = [row]
    db.execute.return_value = result
    mock_session_local.return_value = db

    count = fill_phase(job_id, "parse")

    assert count == 0
    mock_send.assert_not_called()
    mock_reserve.assert_not_called()
    mock_release.assert_not_called()


@patch("aperix_geo.services.sampling.workflow.fill._send_phase_task")
@patch("aperix_geo.services.sampling.workflow.fill.release_response_dispatched")
@patch("aperix_geo.services.sampling.workflow.claim.release_response_claim")
@patch("aperix_geo.services.sampling.workflow.fill.response_claim_active", return_value=True)
@patch("aperix_geo.services.sampling.workflow.fill.shared_redis_client")
def test_reclaim_orphan_dispatch_clears_claim_when_inflight_zero(
    mock_redis_fn: MagicMock,
    _mock_claim_active: MagicMock,
    mock_release_claim: MagicMock,
    mock_release_dispatch: MagicMock,
    mock_send: MagicMock,
) -> None:
    from aperix_geo.services.sampling.workflow.fill import reclaim_stale_response_dispatch

    client = MagicMock()
    client.exists.return_value = True
    client.get.return_value = "0"
    mock_redis_fn.return_value = client

    job_id = uuid4()
    response_id = uuid4()
    reclaim_stale_response_dispatch(job_id, "parse", response_id)

    mock_release_claim.assert_called_once_with(response_id)
    mock_release_dispatch.assert_called_once_with("parse", response_id)
    mock_send.assert_not_called()


@patch("aperix_geo.services.sampling.workflow.fill._soft_fail_orphaned_pending_llm")
@patch("aperix_geo.services.sampling.workflow.fill._send_phase_task")
@patch("aperix_geo.services.sampling.workflow.fill.release_response_dispatched")
@patch("aperix_geo.services.sampling.workflow.claim.release_response_claim")
@patch("aperix_geo.services.sampling.workflow.fill.response_claim_active", return_value=True)
@patch("aperix_geo.services.sampling.workflow.fill.shared_redis_client")
def test_reclaim_orphan_llm_claim_releases_quota(
    mock_redis_fn: MagicMock,
    _mock_claim_active: MagicMock,
    mock_release_claim: MagicMock,
    mock_release_dispatch: MagicMock,
    mock_send: MagicMock,
    mock_soft_fail: MagicMock,
) -> None:
    from aperix_geo.services.sampling.workflow.fill import reclaim_stale_response_dispatch

    client = MagicMock()
    client.exists.return_value = True
    client.get.return_value = "0"
    mock_redis_fn.return_value = client

    response_id = uuid4()
    reclaim_stale_response_dispatch(uuid4(), "llm", response_id)

    mock_release_claim.assert_called_once_with(response_id)
    mock_soft_fail.assert_called_once_with(response_id)
    mock_release_dispatch.assert_called_once_with("llm", response_id)
    mock_send.assert_not_called()


@patch("aperix_geo.services.sampling.workflow.active_job.dispatch_phases", return_value=True)
def test_run_active_job_dispatches_fill(mock_fill: MagicMock) -> None:
    from aperix_geo.services.sampling.workflow.active_job import run_active_job

    job_id = str(uuid4())
    with patch(
        "aperix_geo.services.sampling.workflow.active_job.load_active_job_work",
        return_value=(MagicMock(), True),
    ):
        run_active_job(job_id, ensure_running=True)
    mock_fill.assert_called_once_with(job_id)
