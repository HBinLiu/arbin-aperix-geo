"""Trailing-debounce behavior for sampling finalize scheduling."""

from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import uuid4

from aperix_geo.services.sampling.workflow.finalize import (
    _finalize_armed_key,
    _finalize_dirty_key,
    finalize_sampling_job_db,
    schedule_job_finalize,
)
from aperix_geo.db.models import LLMResponse, LLMResponseStatus, SamplingJob, SamplingJobStatus
from datetime import UTC, datetime
import uuid


@patch("aperix_geo.services.sampling.workflow.finalize.redis_set_nx_strict", return_value=True)
@patch("aperix_geo.services.sampling.workflow.finalize.shared_redis_client")
def test_schedule_job_finalize_uses_trailing_countdown(
    mock_redis: MagicMock,
    mock_nx: MagicMock,
) -> None:
    client = MagicMock()
    mock_redis.return_value = client
    job_id = uuid4()

    with patch("aperix_geo.celery_app.celery_app") as celery:
        schedule_job_finalize(job_id)

    client.set.assert_called_once()
    dirty_key, ex = client.set.call_args[0][0], client.set.call_args[1]["ex"]
    assert dirty_key == _finalize_dirty_key(job_id)
    assert ex >= 5
    mock_nx.assert_called_once_with(_finalize_armed_key(job_id), ttl_s=mock_nx.call_args.kwargs["ttl_s"])
    celery.send_task.assert_called_once()
    assert celery.send_task.call_args.kwargs["countdown"] >= 1
    assert celery.send_task.call_args.args[0] == "aperix_geo.tasks.sampling.sampling_finalize"


@patch("aperix_geo.services.sampling.workflow.finalize.redis_set_nx_strict", return_value=False)
@patch("aperix_geo.services.sampling.workflow.finalize.shared_redis_client")
def test_schedule_job_finalize_skips_when_already_armed(
    mock_redis: MagicMock,
    _mock_nx: MagicMock,
) -> None:
    mock_redis.return_value = MagicMock()
    with patch("aperix_geo.celery_app.celery_app") as celery:
        schedule_job_finalize(uuid4())
    celery.send_task.assert_not_called()


@patch("aperix_geo.services.sampling.workflow.finalize._release_finalize_arm")
def test_finalize_releases_arm_when_still_running(mock_release: MagicMock) -> None:
    """Early finalize must clear :armed so the last item can schedule again."""
    from collections import Counter

    job = SamplingJob(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        subject_id=uuid.uuid4(),
        status=SamplingJobStatus.running,
        total_items=2,
        finished_at=datetime.now(UTC),
    )
    rows = [
        LLMResponse(
            id=uuid.uuid4(),
            sampling_job_id=job.id,
            prompt_id=uuid.uuid4(),
            platform="doubao",
            status=LLMResponseStatus.success,
        ),
        LLMResponse(
            id=uuid.uuid4(),
            sampling_job_id=job.id,
            prompt_id=uuid.uuid4(),
            platform="doubao",
            status=LLMResponseStatus.pending,
        ),
    ]

    class _FakeSession:
        def __init__(self) -> None:
            self._n = 0

        def execute(self, _stmt):  # noqa: ANN001
            self._n += 1
            if self._n == 1:
                return type("R", (), {"scalar_one_or_none": lambda _s: job})()
            counts = Counter(r.status for r in rows)
            return type("R", (), {"all": lambda _s: list(counts.items())})()

        def commit(self) -> None:
            return None

        def refresh(self, _obj) -> None:
            return None

    out = finalize_sampling_job_db(_FakeSession(), job.id)
    assert out is not None
    assert out.status == SamplingJobStatus.running
    mock_release.assert_called_once_with(job.id, terminal=False)


@patch("aperix_geo.services.sampling.workflow.finalize.release_sampling_local_caches")
@patch("aperix_geo.services.sampling.workflow.finalize._release_finalize_arm")
def test_finalize_releases_arm_when_terminal(
    mock_release: MagicMock,
    _mock_caches: MagicMock,
) -> None:
    from collections import Counter

    job = SamplingJob(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        subject_id=uuid.uuid4(),
        status=SamplingJobStatus.running,
        total_items=1,
    )
    rows = [
        LLMResponse(
            id=uuid.uuid4(),
            sampling_job_id=job.id,
            prompt_id=uuid.uuid4(),
            platform="doubao",
            status=LLMResponseStatus.success,
        ),
    ]

    class _FakeSession:
        def __init__(self) -> None:
            self._n = 0

        def execute(self, _stmt):  # noqa: ANN001
            self._n += 1
            if self._n == 1:
                return type("R", (), {"scalar_one_or_none": lambda _s: job})()
            counts = Counter(r.status for r in rows)
            return type("R", (), {"all": lambda _s: list(counts.items())})()

        def commit(self) -> None:
            return None

        def refresh(self, _obj) -> None:
            return None

    with patch(
        "aperix_geo.services.billing.quota.release_remaining_job_quota",
    ):
        out = finalize_sampling_job_db(_FakeSession(), job.id)
    assert out is not None
    assert out.status == SamplingJobStatus.succeed
    mock_release.assert_called_once_with(job.id, terminal=True)
