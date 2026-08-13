"""Tests for sampling job finalize behavior."""

from __future__ import annotations

import uuid
from collections import Counter
from datetime import UTC, datetime

from aperix_geo.db.models import LLMResponse, LLMResponseStatus, SamplingJob, SamplingJobStatus
from aperix_geo.services.sampling.workflow.finalize import finalize_sampling_job_db


def test_finalize_keeps_running_when_crawl_ready_remain() -> None:
    anchor = datetime.now(UTC)
    db = _FakeSession(
        job=SamplingJob(
            id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            subject_id=uuid.uuid4(),
            status=SamplingJobStatus.running,
            total_items=2,
            finished_at=anchor,
        ),
        rows=[
            _row(status=LLMResponseStatus.success),
            _row(status=LLMResponseStatus.crawl_ready),
        ],
    )

    job = finalize_sampling_job_db(db, db.job.id)
    assert job is not None
    assert job.status == SamplingJobStatus.running
    assert job.completed_items == 1
    assert job.finished_at == anchor


def test_finalize_keeps_running_when_llm_ready_remain() -> None:
    anchor = datetime.now(UTC)
    db = _FakeSession(
        job=SamplingJob(
            id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            subject_id=uuid.uuid4(),
            status=SamplingJobStatus.running,
            total_items=2,
            finished_at=anchor,
        ),
        rows=[
            _row(status=LLMResponseStatus.success),
            _row(status=LLMResponseStatus.llm_ready),
        ],
    )

    job = finalize_sampling_job_db(db, db.job.id)
    assert job is not None
    assert job.status == SamplingJobStatus.running
    assert job.completed_items == 1
    assert job.finished_at == anchor


def test_finalize_keeps_running_when_pending_remain() -> None:
    anchor = datetime.now(UTC)
    db = _FakeSession(
        job=SamplingJob(
            id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            subject_id=uuid.uuid4(),
            status=SamplingJobStatus.running,
            total_items=2,
            finished_at=anchor,
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
    assert job.finished_at == anchor


def test_finalize_marks_succeed_when_all_done() -> None:
    db = _FakeSession(
        job=SamplingJob(
            id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            subject_id=uuid.uuid4(),
            status=SamplingJobStatus.running,
            total_items=2,
            quota_open_monthly=0,
            quota_open_pack=0,
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
        counts = Counter(row.status for row in self.rows)
        return _CountResult(list(counts.items()))

    def commit(self) -> None:
        self.committed = True

    def get(self, _model, _pk):  # noqa: ANN001
        return None

    def refresh(self, obj) -> None:  # noqa: ANN001
        if isinstance(obj, SamplingJob):
            obj.updated_at = datetime.now(UTC)


class _JobResult:
    def __init__(self, job: SamplingJob) -> None:
        self._job = job

    def scalar_one_or_none(self) -> SamplingJob:
        return self._job


class _CountResult:
    def __init__(self, rows: list[tuple[LLMResponseStatus, int]]) -> None:
        self._rows = rows

    def all(self) -> list[tuple[LLMResponseStatus, int]]:
        return self._rows
