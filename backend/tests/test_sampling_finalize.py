"""Tests for sampling job finalize behavior."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from aperix_geo.db.models import LLMResponse, LLMResponseStatus, SamplingJob, SamplingJobStatus
from aperix_geo.services.sampling.workflow.finalize import finalize_sampling_job_db


def test_finalize_keeps_running_when_pending_remain() -> None:
    db = _FakeSession(
        job=SamplingJob(
            id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            subject_id=uuid.uuid4(),
            status=SamplingJobStatus.running,
            total_items=2,
        ),
        rows=[
            _row(status=LLMResponseStatus.success),
            _row(status=LLMResponseStatus.pending),
        ],
    )

    job = finalize_sampling_job_db(db, db.job.id)
    assert job is not None
    assert job.status == SamplingJobStatus.running
    assert job.completed_items == 1
    assert job.failed_items == 0
    assert job.finished_at is None


def test_finalize_marks_succeed_when_all_done() -> None:
    db = _FakeSession(
        job=SamplingJob(
            id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            subject_id=uuid.uuid4(),
            status=SamplingJobStatus.running,
            total_items=2,
        ),
        rows=[
            _row(status=LLMResponseStatus.success),
            _row(status=LLMResponseStatus.success),
        ],
    )

    job = finalize_sampling_job_db(db, db.job.id)
    assert job is not None
    assert job.status == SamplingJobStatus.succeed
    assert job.finished_at is not None


def _row(*, status: LLMResponseStatus) -> LLMResponse:
    return LLMResponse(
        id=uuid.uuid4(),
        sampling_job_id=uuid.uuid4(),
        prompt_id=uuid.uuid4(),
        platform="openai",
        status=status,
    )


class _FakeSession:
    def __init__(self, *, job: SamplingJob, rows: list[LLMResponse]) -> None:
        self.job = job
        for row in rows:
            row.sampling_job_id = job.id
        self.rows = rows
        self.committed = False
        self._execute_calls = 0

    def execute(self, _stmt):  # noqa: ANN001
        self._execute_calls += 1
        if self._execute_calls == 1:
            return _JobResult(self.job)
        return _ScalarResult(self.rows)

    def commit(self) -> None:
        self.committed = True

    def refresh(self, obj) -> None:  # noqa: ANN001
        if isinstance(obj, SamplingJob):
            obj.updated_at = datetime.now(UTC)


class _JobResult:
    def __init__(self, job: SamplingJob) -> None:
        self._job = job

    def scalar_one_or_none(self) -> SamplingJob:
        return self._job


class _ScalarResult:
    def __init__(self, rows: list[LLMResponse]) -> None:
        self._rows = rows

    def scalars(self) -> _ScalarResult:
        return self

    def all(self) -> list[LLMResponse]:
        return self._rows
