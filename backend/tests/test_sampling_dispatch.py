"""Tests for sampling chord dispatch debounce."""

from unittest.mock import MagicMock, patch
from uuid import uuid4

from aperix_geo.services.sampling.workflow.dispatch import (
    release_sampling_chord_dispatch,
    try_schedule_sampling_chord_dispatch,
    try_schedule_sampling_orchestration_task,
)


@patch("aperix_geo.services.sampling.workflow.dispatch.redis_set_nx_strict")
def test_chord_dispatch_allows_empty_response_set(mock_set_nx: MagicMock) -> None:
    assert try_schedule_sampling_chord_dispatch(uuid4(), []) is True
    mock_set_nx.assert_not_called()


@patch("aperix_geo.services.sampling.workflow.dispatch.redis_set_nx_strict", return_value=True)
def test_chord_dispatch_acquires_per_job_lock(mock_set_nx: MagicMock) -> None:
    job_id = uuid4()

    assert try_schedule_sampling_chord_dispatch(job_id, ["a", "b"]) is True

    mock_set_nx.assert_called_once()
    key = mock_set_nx.call_args.args[0]
    assert str(job_id) in key
    assert "job_chord" in key


@patch("aperix_geo.services.sampling.workflow.dispatch.redis_set_nx_strict", return_value=False)
def test_chord_dispatch_blocks_duplicate_job_lock(mock_set_nx: MagicMock) -> None:
    job_id = uuid4()
    assert try_schedule_sampling_chord_dispatch(job_id, ["x"]) is False


@patch("aperix_geo.services.sampling.workflow.dispatch.redis_delete")
def test_release_sampling_chord_dispatch(mock_delete: MagicMock) -> None:
    job_id = uuid4()
    release_sampling_chord_dispatch(job_id)
    key = mock_delete.call_args.args[0]
    assert str(job_id) in key
    assert "job_chord" in key


@patch("aperix_geo.services.sampling.workflow.dispatch.redis_set_nx_strict", return_value=True)
def test_orchestrate_task_acquires_debounce_key(mock_set_nx: MagicMock) -> None:
    job_id = uuid4()
    assert try_schedule_sampling_orchestration_task(job_id) is True
    key = mock_set_nx.call_args.args[0]
    assert str(job_id) in key
    assert "orchestrate" in key


@patch("aperix_geo.services.sampling.workflow.orchestrate.celery_app.send_task")
@patch(
    "aperix_geo.services.sampling.workflow.dispatch.try_schedule_sampling_orchestration_task",
    return_value=False,
)
def test_enqueue_sampling_orchestration_skips_when_debounced(
    mock_try: MagicMock,
    mock_send: MagicMock,
) -> None:
    from aperix_geo.services.sampling.workflow.orchestrate import enqueue_sampling_orchestration

    job_id = uuid4()
    enqueue_sampling_orchestration(job_id)
    mock_try.assert_called_once_with(job_id)
    mock_send.assert_not_called()
