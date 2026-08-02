"""Tests for sampling task claim + short row lock."""

from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import uuid4

from aperix_geo.db.models import LLMResponse, LLMResponseStatus, SamplingJob, Subject, SubjectType
from aperix_geo.services.billing.exceptions import SubscriptionInactiveError
from aperix_geo.services.providers.result import SamplingChatResult
from aperix_geo.services.sampling.parsed import ParsedSamplingResult
from aperix_geo.services.sampling.workflow.phase_specs import build_llm_phase_spec
from aperix_geo.tasks.sampling import sampling_crawl, sampling_llm, sampling_parse


def _pending_row() -> LLMResponse:
    return LLMResponse(
        id=uuid4(),
        sampling_job_id=uuid4(),
        prompt_id=uuid4(),
        platform="doubao",
        status=LLMResponseStatus.pending,
    )


def _llm_ready_row() -> LLMResponse:
    row = _pending_row()
    row.status = LLMResponseStatus.llm_ready
    row.raw_text = "answer"
    row.parsed = {"source_urls_from_api": [], "web_search_mode": "none"}
    return row


def _crawl_ready_row() -> LLMResponse:
    row = _llm_ready_row()
    row.status = LLMResponseStatus.crawl_ready
    return row


@patch("aperix_geo.services.sampling.workflow.phase_specs.require_active_subscription")
@patch("aperix_geo.services.sampling.workflow.fill.on_task_claim_lost")
@patch("aperix_geo.services.sampling.workflow.fill.on_task_finished")
@patch("aperix_geo.services.sampling.workflow.phase.release_response_claim")
@patch("aperix_geo.services.sampling.workflow.phase.try_claim_response", return_value=False)
@patch("aperix_geo.services.sampling.workflow.phase_specs.load_subject_with_competitors_cached")
@patch("aperix_geo.services.sampling.workflow.phase_specs.load_prompt_text_cached", return_value="prompt")
@patch("aperix_geo.services.sampling.workflow.phase.SessionLocal")
def test_sample_llm_prompt_skips_when_claim_lost(
    mock_session_local: MagicMock,
    _mock_prompt: MagicMock,
    mock_subject: MagicMock,
    _mock_claim: MagicMock,
    mock_release: MagicMock,
    mock_on_finished: MagicMock,
    mock_on_claim_lost: MagicMock,
    _mock_sub: MagicMock,
) -> None:
    row = _pending_row()
    job = SamplingJob(id=row.sampling_job_id, tenant_id=uuid4(), subject_id=uuid4())
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

    out = sampling_llm.run(str(row.id))

    assert out == {"ok": True, "skipped": True, "reason": "claimed"}
    db.commit.assert_called()
    mock_release.assert_not_called()
    mock_on_claim_lost.assert_called_once()
    mock_on_finished.assert_not_called()


@patch("aperix_geo.services.sampling.workflow.phase_specs.require_active_subscription")
@patch("aperix_geo.services.sampling.workflow.phase.release_response_claim")
@patch("aperix_geo.services.sampling.workflow.phase.refresh_response_claim")
@patch("aperix_geo.services.sampling.workflow.phase_specs.clear_cached_llm_result")
@patch("aperix_geo.services.sampling.workflow.phase_specs.persist_llm_sample", return_value=True)
@patch("aperix_geo.services.sampling.workflow.phase_specs.prepare_sample_chat_result")
@patch("aperix_geo.services.sampling.workflow.phase.try_claim_response", return_value=True)
@patch("aperix_geo.services.sampling.workflow.phase_specs.load_subject_with_competitors_cached")
@patch("aperix_geo.services.sampling.workflow.phase_specs.load_prompt_text_cached", return_value="prompt")
@patch("aperix_geo.services.sampling.workflow.phase.SessionLocal")
def test_sample_llm_prompt_releases_claim_after_success(
    mock_session_local: MagicMock,
    _mock_prompt: MagicMock,
    mock_subject: MagicMock,
    _mock_claim: MagicMock,
    mock_prepare: MagicMock,
    mock_persist: MagicMock,
    _mock_refresh: MagicMock,
    mock_clear: MagicMock,
    mock_release: MagicMock,
    _mock_sub: MagicMock,
) -> None:
    row = _pending_row()
    job = SamplingJob(id=row.sampling_job_id, tenant_id=uuid4(), subject_id=uuid4())
    subject = Subject(
        id=job.subject_id,
        tenant_id=uuid4(),
        type=SubjectType.brand,
        brand="Aperix",
    )
    mock_subject.return_value = subject
    chat_result = SamplingChatResult(text="ok", usage={}, latency_ms=0, source_urls=())
    mock_prepare.return_value = (chat_result, True)

    db = MagicMock()
    lock_result = MagicMock()
    lock_result.scalar_one_or_none.return_value = row
    db.execute.return_value = lock_result
    db.get.return_value = job
    mock_session_local.return_value = db

    out = sampling_llm.run(str(row.id))

    assert out == {"ok": True, "phase": "llm"}
    mock_prepare.assert_called_once()
    mock_persist.assert_called_once()
    mock_clear.assert_called_once()
    mock_release.assert_called_once()


@patch("aperix_geo.services.sampling.workflow.phase.release_response_claim")
@patch("aperix_geo.services.sampling.workflow.phase_specs.persist_crawl_sample", return_value=True)
@patch("aperix_geo.services.sampling.workflow.phase_specs.crawl_response_citations")
@patch("aperix_geo.services.sampling.workflow.phase.try_claim_response", return_value=True)
@patch("aperix_geo.services.sampling.workflow.phase_specs.load_subject_with_competitors_cached")
@patch("aperix_geo.services.sampling.workflow.phase.SessionLocal")
def test_sample_crawl_response_runs_crawl_phase(
    mock_session_local: MagicMock,
    mock_subject: MagicMock,
    _mock_claim: MagicMock,
    mock_crawl: MagicMock,
    mock_persist: MagicMock,
    mock_release: MagicMock,
) -> None:
    row = _llm_ready_row()
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

    out = sampling_crawl.run(str(row.id))

    assert out == {"ok": True, "phase": "crawl"}
    mock_crawl.assert_called_once()
    mock_persist.assert_called_once()
    mock_release.assert_called_once()


@patch("aperix_geo.services.brand.backfill.maybe_enqueue_brand_domain_backfill")
@patch("aperix_geo.services.sampling.workflow.phase.release_response_claim")
@patch("aperix_geo.services.sampling.workflow.phase_specs.persist_parsed_sample", return_value=True)
@patch("aperix_geo.services.sampling.workflow.phase_specs.parse_llm_output")
@patch("aperix_geo.services.sampling.workflow.phase.try_claim_response", return_value=True)
@patch("aperix_geo.services.sampling.workflow.phase_specs.load_subject_with_competitors_cached")
@patch("aperix_geo.services.sampling.workflow.phase.SessionLocal")
def test_sample_parse_response_runs_parse_phase(
    mock_session_local: MagicMock,
    mock_subject: MagicMock,
    _mock_claim: MagicMock,
    mock_parse: MagicMock,
    mock_persist: MagicMock,
    mock_release: MagicMock,
    _mock_backfill: MagicMock,
) -> None:
    row = _crawl_ready_row()
    job = SamplingJob(id=row.sampling_job_id, subject_id=uuid4())
    subject = Subject(
        id=job.subject_id,
        tenant_id=uuid4(),
        type=SubjectType.brand,
        brand="Aperix",
    )
    mock_subject.return_value = subject
    mock_parse.return_value = ParsedSamplingResult()

    db = MagicMock()
    lock_result = MagicMock()
    lock_result.scalar_one_or_none.return_value = row
    db.execute.return_value = lock_result
    db.get.return_value = job
    mock_session_local.return_value = db

    out = sampling_parse.run(str(row.id))

    assert out == {"ok": True, "phase": "parse"}
    mock_parse.assert_called_once()
    mock_persist.assert_called_once()
    mock_release.assert_called_once()


@patch("aperix_geo.services.sampling.workflow.execute._release_response_quota")
@patch("aperix_geo.services.sampling.workflow.claim.shared_redis_client", return_value=None)
def test_soft_skip_writes_reason_marker(
    _mock_redis: MagicMock,
    mock_release: MagicMock,
) -> None:
    from aperix_geo.services.sampling.workflow.execute import (
        SOFT_SKIP_SUBSCRIPTION_INACTIVE,
        soft_skip_pending_llm_responses,
    )

    row = _pending_row()
    db = MagicMock()
    db.execute.return_value.scalars.return_value.all.return_value = [row]

    skipped = soft_skip_pending_llm_responses(db, job_id=row.sampling_job_id)

    assert skipped == 1
    assert row.status == LLMResponseStatus.failed
    assert row.error_text == SOFT_SKIP_SUBSCRIPTION_INACTIVE
    mock_release.assert_called_once()


@patch(
    "aperix_geo.services.sampling.workflow.phase_specs.require_active_subscription",
    side_effect=SubscriptionInactiveError("expired"),
)
@patch("aperix_geo.services.sampling.workflow.phase_specs.soft_skip_pending_llm_responses")
@patch("aperix_geo.services.sampling.workflow.phase_specs.load_subject_with_competitors_cached")
@patch("aperix_geo.services.sampling.workflow.phase_specs.load_prompt_text_cached", return_value="prompt")
def test_llm_prepare_soft_skips_when_subscription_expired(
    _mock_prompt: MagicMock,
    mock_subject: MagicMock,
    mock_soft_skip: MagicMock,
    _mock_sub: MagicMock,
) -> None:
    mock_subject.return_value = Subject(
        id=uuid4(),
        tenant_id=uuid4(),
        type=SubjectType.brand,
        brand="Aperix",
    )
    row = _pending_row()
    job = SamplingJob(id=row.sampling_job_id, tenant_id=uuid4(), subject_id=uuid4())
    spec = build_llm_phase_spec(MagicMock(), str(row.id))
    db = MagicMock()

    out = spec.prepare(db, row, job)

    from aperix_geo.services.sampling.workflow.execute import SOFT_SKIP_SUBSCRIPTION_INACTIVE

    assert out == {"ok": True, "skipped": True, "reason": SOFT_SKIP_SUBSCRIPTION_INACTIVE}
    mock_soft_skip.assert_called_once_with(
        db, job_id=job.id, reason=SOFT_SKIP_SUBSCRIPTION_INACTIVE
    )


@patch(
    "aperix_geo.services.sampling.workflow.phase_specs.require_active_subscription",
    side_effect=SubscriptionInactiveError("expired"),
)
@patch("aperix_geo.services.sampling.workflow.phase_specs.parse_llm_output")
@patch("aperix_geo.services.sampling.workflow.phase_specs.load_subject_with_competitors_cached")
def test_parse_prepare_skips_absa_when_subscription_expired(
    mock_subject: MagicMock,
    mock_parse: MagicMock,
    _mock_sub: MagicMock,
) -> None:
    from aperix_geo.services.sampling.workflow.phase_specs import build_parse_phase_spec

    mock_subject.return_value = Subject(
        id=uuid4(),
        tenant_id=uuid4(),
        type=SubjectType.brand,
        brand="Aperix",
    )
    mock_parse.return_value = ParsedSamplingResult()
    row = _crawl_ready_row()
    job = SamplingJob(id=row.sampling_job_id, tenant_id=uuid4(), subject_id=uuid4())
    spec = build_parse_phase_spec(MagicMock(), str(row.id))

    assert spec.prepare(MagicMock(), row, job) is None
    spec.work()
    assert mock_parse.call_args.kwargs["skip_absa"] is True

