"""Tests for batched sampling chord dispatch."""

from unittest.mock import MagicMock, patch
from uuid import uuid4

from aperix_geo.services.sampling.workflow.dispatch import sampling_chord_batch


def test_sampling_chord_batch_limits_to_batch_size() -> None:
    ids = [f"id-{i}" for i in range(25)]
    assert sampling_chord_batch(ids, batch_size=10) == ids[:10]
    assert sampling_chord_batch(ids, batch_size=25) == ids
    assert sampling_chord_batch(ids[:3], batch_size=10) == ids[:3]


@patch("aperix_geo.services.sampling.workflow.chord.chord")
@patch("aperix_geo.services.sampling.workflow.chord.group")
@patch("aperix_geo.services.sampling.workflow.chord.try_schedule_sampling_chord_dispatch", return_value=True)
@patch("aperix_geo.services.sampling.workflow.chord.response_work_queues")
@patch("aperix_geo.services.sampling.workflow.chord.SessionLocal")
def test_dispatch_next_chord_schedules_llm_batch(
    mock_session_local: MagicMock,
    mock_queues: MagicMock,
    mock_try_dispatch: MagicMock,
    mock_group: MagicMock,
    mock_chord: MagicMock,
) -> None:
    from aperix_geo.services.sampling.workflow.chord import dispatch_next_chord

    job_id = uuid4()
    pending = [uuid4() for _ in range(15)]
    mock_queues.return_value.pending = tuple(pending)
    mock_queues.return_value.llm_ready = ()
    mock_queues.return_value.crawl_ready = ()
    mock_queues.return_value.pending_strs = [str(response_id) for response_id in pending]
    mock_session_local.return_value = MagicMock()

    assert dispatch_next_chord(str(job_id)) is True

    mock_try_dispatch.assert_called_once()
    dispatched_batch = mock_try_dispatch.call_args.args[1]
    assert dispatched_batch == [str(response_id) for response_id in pending[:10]]

    mock_group.assert_called_once()
    scheduled = list(mock_group.call_args.args[0])
    assert len(scheduled) == 10
    mock_chord.assert_called_once()


@patch("aperix_geo.services.sampling.workflow.chord.chord")
@patch("aperix_geo.services.sampling.workflow.chord.group")
@patch("aperix_geo.services.sampling.workflow.chord.try_schedule_sampling_chord_dispatch", return_value=True)
@patch("aperix_geo.services.sampling.workflow.chord.response_work_queues")
@patch("aperix_geo.services.sampling.workflow.chord.SessionLocal")
def test_dispatch_next_chord_schedules_crawl_batch_when_llm_done(
    mock_session_local: MagicMock,
    mock_queues: MagicMock,
    mock_try_dispatch: MagicMock,
    mock_group: MagicMock,
    mock_chord: MagicMock,
) -> None:
    from aperix_geo.services.sampling.workflow.chord import dispatch_next_chord

    job_id = uuid4()
    llm_ready = [uuid4() for _ in range(3)]
    mock_queues.return_value.pending = ()
    mock_queues.return_value.llm_ready = tuple(llm_ready)
    mock_queues.return_value.crawl_ready = ()
    mock_queues.return_value.llm_ready_strs = [str(response_id) for response_id in llm_ready]
    mock_session_local.return_value = MagicMock()

    assert dispatch_next_chord(str(job_id)) is True

    dispatched_batch = mock_try_dispatch.call_args.args[1]
    assert dispatched_batch == [str(response_id) for response_id in llm_ready]
    assert len(list(mock_group.call_args.args[0])) == 3


@patch("aperix_geo.services.sampling.workflow.chord.chord")
@patch("aperix_geo.services.sampling.workflow.chord.group")
@patch("aperix_geo.services.sampling.workflow.chord.try_schedule_sampling_chord_dispatch", return_value=True)
@patch("aperix_geo.services.sampling.workflow.chord.response_work_queues")
@patch("aperix_geo.services.sampling.workflow.chord.SessionLocal")
def test_dispatch_next_chord_schedules_parse_batch_when_crawl_done(
    mock_session_local: MagicMock,
    mock_queues: MagicMock,
    mock_try_dispatch: MagicMock,
    mock_group: MagicMock,
    mock_chord: MagicMock,
) -> None:
    from aperix_geo.services.sampling.workflow.chord import dispatch_next_chord

    job_id = uuid4()
    crawl_ready = [uuid4() for _ in range(2)]
    mock_queues.return_value.pending = ()
    mock_queues.return_value.llm_ready = ()
    mock_queues.return_value.crawl_ready = tuple(crawl_ready)
    mock_queues.return_value.crawl_ready_strs = [str(response_id) for response_id in crawl_ready]
    mock_session_local.return_value = MagicMock()

    assert dispatch_next_chord(str(job_id)) is True

    dispatched_batch = mock_try_dispatch.call_args.args[1]
    assert dispatched_batch == [str(response_id) for response_id in crawl_ready]
    assert len(list(mock_group.call_args.args[0])) == 2


@patch("aperix_geo.services.sampling.workflow.chord.response_work_queues")
@patch("aperix_geo.services.sampling.workflow.chord.SessionLocal")
def test_dispatch_next_chord_skips_when_idle(
    mock_session_local: MagicMock,
    mock_queues: MagicMock,
) -> None:
    from aperix_geo.services.sampling.workflow.chord import dispatch_next_chord

    mock_queues.return_value.pending = ()
    mock_queues.return_value.llm_ready = ()
    mock_queues.return_value.crawl_ready = ()
    mock_session_local.return_value = MagicMock()
    assert dispatch_next_chord(str(uuid4())) is False


@patch("aperix_geo.tasks.sampling.dispatch_next_chord")
@patch("aperix_geo.services.sampling.workflow.dispatch.release_sampling_chord_dispatch")
@patch("aperix_geo.tasks.sampling.finalize_sampling_job_db")
@patch("aperix_geo.tasks.sampling.SessionLocal")
def test_finalize_job_chains_next_batch(
    mock_session_local: MagicMock,
    mock_finalize_db: MagicMock,
    mock_release: MagicMock,
    mock_dispatch: MagicMock,
) -> None:
    from aperix_geo.tasks.sampling import sampling_finalize

    job_id = uuid4()
    mock_session_local.return_value = MagicMock()
    sampling_finalize([], str(job_id))

    mock_finalize_db.assert_called_once()
    mock_release.assert_called_once_with(job_id)
    mock_dispatch.assert_called_once_with(str(job_id))


@patch("aperix_geo.tasks.sampling.run_active_job")
def test_orchestrate_delegates_to_run_active_job(mock_run_active: MagicMock) -> None:
    from aperix_geo.tasks.sampling import sampling_orchestrate

    job_id = uuid4()
    sampling_orchestrate(str(job_id))
    mock_run_active.assert_called_once_with(str(job_id), ensure_running=True)
