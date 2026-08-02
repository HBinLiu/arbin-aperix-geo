"""Tests for user-triggered sampling retry quota / subscription gates."""

from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from aperix_geo.db.models import LLMResponse, LLMResponseStatus, SamplingJob, SamplingJobStatus, Subject, SubjectType
from aperix_geo.services.billing.exceptions import SubscriptionInactiveError
from aperix_geo.services.sampling.workflow.jobs import SamplingJobError
from aperix_geo.services.sampling.workflow.retry_user import retry_subject_sampling


def _subject() -> Subject:
    return Subject(
        id=uuid4(),
        tenant_id=uuid4(),
        type=SubjectType.brand,
        brand="Aperix",
        website_url="https://aperix.com",
    )


@patch(
    "aperix_geo.services.sampling.workflow.retry_user.require_active_subscription",
    side_effect=SubscriptionInactiveError("expired"),
)
def test_retry_rejects_expired_subscription(_mock_sub: MagicMock) -> None:
    subject = _subject()
    with pytest.raises(SamplingJobError, match="订阅已过期"):
        retry_subject_sampling(MagicMock(), subject=subject, tenant_id=subject.tenant_id)


@patch("aperix_geo.services.sampling.workflow.orchestrate.enqueue_sampling_continue")
@patch("aperix_geo.services.sampling.workflow.retry_user.reserve_ai_usage")
@patch("aperix_geo.services.sampling.workflow.retry_user.lock_tenant_ai_quota", return_value=2)
@patch("aperix_geo.services.sampling.workflow.retry_user.require_active_subscription")
@patch("aperix_geo.services.sampling.workflow.retry_user.subject_has_active_sampling_job", return_value=False)
@patch("aperix_geo.services.sampling.workflow.retry_user.get_latest_sampling_job")
@patch("aperix_geo.services.sampling.workflow.retry_user.response_work_queues")
def test_retry_failed_without_raw_text_reserves_and_resets_settled(
    mock_queues: MagicMock,
    mock_latest: MagicMock,
    _mock_active: MagicMock,
    _mock_sub: MagicMock,
    _mock_lock: MagicMock,
    mock_reserve: MagicMock,
    _mock_continue: MagicMock,
) -> None:
    subject = _subject()
    job = SamplingJob(
        id=uuid4(),
        tenant_id=subject.tenant_id,
        subject_id=subject.id,
        status=SamplingJobStatus.failed,
    )
    row = LLMResponse(
        id=uuid4(),
        sampling_job_id=job.id,
        prompt_id=uuid4(),
        platform="doubao",
        status=LLMResponseStatus.failed,
        raw_text="",
        quota_settled=True,
    )
    mock_latest.return_value = job
    mock_queues.return_value = MagicMock(has_work=False)

    failed_exists = MagicMock()
    failed_exists.scalar_one_or_none.return_value = row.id
    failed_rows = MagicMock()
    failed_rows.scalars.return_value.all.return_value = [row]
    db = MagicMock()
    db.execute.side_effect = [failed_exists, failed_rows]

    out = retry_subject_sampling(db, subject=subject, tenant_id=subject.tenant_id)

    assert out is job
    assert row.status == LLMResponseStatus.pending
    assert row.quota_settled is False
    mock_reserve.assert_called_once()
    assert mock_reserve.call_args.kwargs["amount"] == 1
    assert mock_reserve.call_args.kwargs["job"] is job
    db.commit.assert_called()


@patch("aperix_geo.services.sampling.workflow.orchestrate.enqueue_sampling_continue")
@patch("aperix_geo.services.sampling.workflow.retry_user.reserve_ai_usage")
@patch("aperix_geo.services.sampling.workflow.retry_user.require_active_subscription")
@patch("aperix_geo.services.sampling.workflow.retry_user.subject_has_active_sampling_job", return_value=False)
@patch("aperix_geo.services.sampling.workflow.retry_user.get_latest_sampling_job")
@patch("aperix_geo.services.sampling.workflow.retry_user.response_work_queues")
def test_retry_failed_with_raw_text_goes_llm_ready_without_reserve(
    mock_queues: MagicMock,
    mock_latest: MagicMock,
    _mock_active: MagicMock,
    _mock_sub: MagicMock,
    mock_reserve: MagicMock,
    _mock_continue: MagicMock,
) -> None:
    subject = _subject()
    job = SamplingJob(
        id=uuid4(),
        tenant_id=subject.tenant_id,
        subject_id=subject.id,
        status=SamplingJobStatus.failed,
    )
    row = LLMResponse(
        id=uuid4(),
        sampling_job_id=job.id,
        prompt_id=uuid4(),
        platform="doubao",
        status=LLMResponseStatus.failed,
        raw_text="already sampled",
        quota_settled=True,
    )
    mock_latest.return_value = job
    mock_queues.return_value = MagicMock(has_work=False)

    failed_exists = MagicMock()
    failed_exists.scalar_one_or_none.return_value = row.id
    failed_rows = MagicMock()
    failed_rows.scalars.return_value.all.return_value = [row]
    db = MagicMock()
    db.execute.side_effect = [failed_exists, failed_rows]

    retry_subject_sampling(db, subject=subject, tenant_id=subject.tenant_id)

    assert row.status == LLMResponseStatus.llm_ready
    assert row.quota_settled is True
    mock_reserve.assert_not_called()
