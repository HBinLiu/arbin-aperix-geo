"""Tests for sampling orchestration debounce."""

from unittest.mock import MagicMock, patch
from uuid import uuid4

from aperix_geo.services.sampling.workflow.dispatch import try_schedule_sampling_job_enqueue


@patch("aperix_geo.services.sampling.workflow.dispatch.redis_set_nx_strict", return_value=True)
def test_orchestrate_task_acquires_debounce_key(mock_set_nx: MagicMock) -> None:
    job_id = uuid4()
    assert try_schedule_sampling_job_enqueue(job_id) is True
    key = mock_set_nx.call_args.args[0]
    assert str(job_id) in key
    assert "job_enqueue" in key


@patch("aperix_geo.services.sampling.workflow.orchestrate.celery_app.send_task")
@patch(
    "aperix_geo.services.sampling.workflow.dispatch.try_schedule_sampling_job_enqueue",
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
