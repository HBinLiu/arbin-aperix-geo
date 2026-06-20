"""Tests for sampling task claim + short row lock."""

from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import uuid4

from aperix_geo.db.models import LLMResponse, LLMResponseStatus, SamplingJob, Subject, SubjectType
from aperix_geo.services.providers.result import SamplingChatResult
from aperix_geo.services.sampling.parsed import ParsedSamplingResult
from aperix_geo.tasks.sampling import sample_one_prompt


def _pending_row() -> LLMResponse:
    return LLMResponse(
        id=uuid4(),
        sampling_job_id=uuid4(),
        prompt_id=uuid4(),
        platform="doubao",
        status=LLMResponseStatus.pending,
    )


@patch("aperix_geo.tasks.sampling.release_response_claim")
@patch("aperix_geo.tasks.sampling.try_claim_response", return_value=False)
@patch("aperix_geo.tasks.sampling.load_subject_with_competitors_cached")
@patch("aperix_geo.tasks.sampling.load_prompt_text_cached", return_value="prompt")
@patch("aperix_geo.tasks.sampling.check_llm_rate_limit")
@patch("aperix_geo.tasks.sampling.SessionLocal")
def test_sample_one_prompt_skips_when_claim_lost(
    mock_session_local: MagicMock,
    _mock_rate: MagicMock,
    _mock_prompt: MagicMock,
    mock_subject: MagicMock,
    _mock_claim: MagicMock,
    mock_release: MagicMock,
) -> None:
    row = _pending_row()
    job = SamplingJob(id=row.sampling_job_id, subject_id=uuid4())
    subject = Subject(
        id=job.subject_id,
        tenant_id=uuid4(),
        type=SubjectType.brand,
        brand="Aperix",
    )
    mock_subject.return_value = subject

    db = MagicMock()
    lock_result = MagicMock()
    lock_result.scalar_one_or_none.return_value = row
    db.execute.return_value = lock_result
    db.get.return_value = job
    mock_session_local.return_value = db

    task = MagicMock()
    task.request.retries = 0

    out = sample_one_prompt.run(str(row.id))

    assert out == {"ok": True, "skipped": True, "reason": "claimed"}
    db.commit.assert_called()
    mock_release.assert_not_called()


@patch("aperix_geo.services.brand.backfill.maybe_enqueue_brand_domain_backfill")
@patch("aperix_geo.tasks.sampling.release_response_claim")
@patch("aperix_geo.tasks.sampling.persist_sample_if_pending", return_value=True)
@patch("aperix_geo.tasks.sampling.execute_sample_without_row_lock")
@patch("aperix_geo.tasks.sampling.try_claim_response", return_value=True)
@patch("aperix_geo.tasks.sampling.load_subject_with_competitors_cached")
@patch("aperix_geo.tasks.sampling.load_prompt_text_cached", return_value="prompt")
@patch("aperix_geo.tasks.sampling.check_llm_rate_limit")
@patch("aperix_geo.tasks.sampling.SessionLocal")
def test_sample_one_prompt_releases_claim_after_success(
    mock_session_local: MagicMock,
    _mock_rate: MagicMock,
    _mock_prompt: MagicMock,
    mock_subject: MagicMock,
    _mock_claim: MagicMock,
    mock_execute: MagicMock,
    mock_persist: MagicMock,
    mock_release: MagicMock,
    mock_backfill: MagicMock,
) -> None:
    row = _pending_row()
    job = SamplingJob(id=row.sampling_job_id, subject_id=uuid4())
    subject = Subject(
        id=job.subject_id,
        tenant_id=uuid4(),
        type=SubjectType.brand,
        brand="Aperix",
    )
    mock_subject.return_value = subject
    parsed = ParsedSamplingResult()
    mock_execute.return_value = (
        SamplingChatResult(text="ok", usage={}, latency_ms=0, source_urls=()),
        parsed,
    )

    db = MagicMock()
    lock_result = MagicMock()
    lock_result.scalar_one_or_none.return_value = row
    db.execute.return_value = lock_result
    db.get.return_value = job
    mock_session_local.return_value = db

    task = MagicMock()
    task.request.retries = 0

    out = sample_one_prompt.run(str(row.id))

    assert out == {"ok": True}
    mock_persist.assert_called_once()
    mock_release.assert_called_once_with(row.id)
    mock_backfill.assert_called_once_with(row.id)
