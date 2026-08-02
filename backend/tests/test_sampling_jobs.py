"""Tests for sampling job creation guards."""

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from aperix_geo.db.models import LLMResponse, Prompt, Subject, SubjectType
from aperix_geo.services.billing.exceptions import SubscriptionInactiveError
from aperix_geo.services.sampling.workflow.jobs import SamplingJobError, create_and_enqueue_sampling_job


def _subject() -> Subject:
    return Subject(
        id=uuid4(),
        tenant_id=uuid4(),
        type=SubjectType.brand,
        brand="Aperix",
        website_url="https://aperix.com",
    )


def _prompt(subject: Subject, *, text: str = "test prompt") -> Prompt:
    return Prompt(
        id=uuid4(),
        subject_id=subject.id,
        text=text,
        text_hash="hash",
        enabled=True,
    )


def _mock_db(subject: Subject, prompts: list[Prompt]) -> MagicMock:
    db = MagicMock()
    prompt_result = MagicMock()
    prompt_result.scalars.return_value.all.return_value = prompts
    subject_result = MagicMock()
    subject_result.scalar_one_or_none.return_value = subject
    db.execute.side_effect = [prompt_result, subject_result]
    return db


@patch("aperix_geo.services.sampling.workflow.jobs.lock_tenant_ai_quota", return_value=10)
@patch("aperix_geo.services.sampling.workflow.jobs.reserve_ai_usage")
@patch("aperix_geo.services.sampling.workflow.jobs.require_active_subscription")
@patch("aperix_geo.services.sampling.workflow.orchestrate.enqueue_sampling_orchestration")
@patch("aperix_geo.services.sampling.workflow.jobs.subject_has_active_sampling_job", return_value=False)
def test_create_sampling_job_locks_subject_and_succeeds(
    _mock_active: MagicMock,
    mock_enqueue: MagicMock,
    _mock_sub: MagicMock,
    mock_reserve: MagicMock,
    _mock_available: MagicMock,
) -> None:
    subject = _subject()
    prompt = _prompt(subject)
    db = _mock_db(subject, [prompt])

    job = create_and_enqueue_sampling_job(
        db,
        subject=subject,
        tenant_id=subject.tenant_id,
        platforms=["doubao"],
    )

    assert job.total_items == 1
    mock_reserve.assert_called_once()
    assert mock_reserve.call_args.kwargs["amount"] == 1
    db.commit.assert_called_once()
    mock_enqueue.assert_called_once()


@patch("aperix_geo.services.sampling.workflow.jobs.require_active_subscription")
@patch("aperix_geo.services.sampling.workflow.jobs.subject_has_active_sampling_job", return_value=True)
def test_create_sampling_job_rejects_active_job(
    _mock_active: MagicMock,
    _mock_sub: MagicMock,
) -> None:
    subject = _subject()
    prompt = _prompt(subject)
    db = _mock_db(subject, [prompt])

    with pytest.raises(SamplingJobError, match="already queued or running"):
        create_and_enqueue_sampling_job(
            db,
            subject=subject,
            tenant_id=subject.tenant_id,
            platforms=["doubao"],
        )

    db.commit.assert_not_called()


@patch(
    "aperix_geo.services.sampling.workflow.jobs.require_active_subscription",
    side_effect=SubscriptionInactiveError("expired"),
)
def test_create_sampling_job_rejects_expired_subscription(_mock_sub: MagicMock) -> None:
    subject = _subject()
    prompt = _prompt(subject)
    db = _mock_db(subject, [prompt])

    with pytest.raises(SamplingJobError, match="订阅已过期"):
        create_and_enqueue_sampling_job(
            db,
            subject=subject,
            tenant_id=subject.tenant_id,
            platforms=["doubao"],
        )

    db.commit.assert_not_called()


@patch("aperix_geo.services.sampling.workflow.jobs.lock_tenant_ai_quota", return_value=0)
@patch("aperix_geo.services.sampling.workflow.jobs.require_active_subscription")
@patch("aperix_geo.services.sampling.workflow.jobs.subject_has_active_sampling_job", return_value=False)
def test_create_sampling_job_rejects_zero_quota(
    _mock_active: MagicMock,
    _mock_sub: MagicMock,
    _mock_available: MagicMock,
) -> None:
    subject = _subject()
    prompt = _prompt(subject)
    db = _mock_db(subject, [prompt])

    with pytest.raises(SamplingJobError, match="AI 调用额度不足"):
        create_and_enqueue_sampling_job(
            db,
            subject=subject,
            tenant_id=subject.tenant_id,
            platforms=["doubao"],
        )

    db.rollback.assert_called_once()
    db.commit.assert_not_called()


@patch("aperix_geo.services.sampling.workflow.jobs.lock_tenant_ai_quota", return_value=0)
@patch("aperix_geo.services.sampling.workflow.jobs.subject_has_active_sampling_job", return_value=False)
def test_create_sampling_job_zero_quota_reports_expired_subscription(
    _mock_active: MagicMock,
    _mock_available: MagicMock,
) -> None:
    subject = _subject()
    prompt = _prompt(subject)
    db = _mock_db(subject, [prompt])
    calls = {"n": 0}

    def _require(_db: object, _tenant_id: object, **_kwargs: object) -> None:
        calls["n"] += 1
        if calls["n"] >= 2:
            raise SubscriptionInactiveError("expired")

    with (
        patch(
            "aperix_geo.services.sampling.workflow.jobs.require_active_subscription",
            side_effect=_require,
        ),
        pytest.raises(SamplingJobError, match="订阅已过期"),
    ):
        create_and_enqueue_sampling_job(
            db,
            subject=subject,
            tenant_id=subject.tenant_id,
            platforms=["doubao"],
        )


@patch("aperix_geo.services.sampling.workflow.jobs.lock_tenant_ai_quota", return_value=4)
@patch("aperix_geo.services.sampling.workflow.jobs.reserve_ai_usage")
@patch("aperix_geo.services.sampling.workflow.jobs.require_active_subscription")
@patch("aperix_geo.services.sampling.workflow.orchestrate.enqueue_sampling_orchestration")
@patch("aperix_geo.services.sampling.workflow.jobs.subject_has_active_sampling_job", return_value=False)
def test_create_sampling_job_truncates_platform_first(
    _mock_active: MagicMock,
    mock_enqueue: MagicMock,
    _mock_sub: MagicMock,
    mock_reserve: MagicMock,
    _mock_available: MagicMock,
) -> None:
    subject = _subject()
    prompts = [_prompt(subject, text=f"p{i}") for i in range(3)]
    db = _mock_db(subject, prompts)

    job = create_and_enqueue_sampling_job(
        db,
        subject=subject,
        tenant_id=subject.tenant_id,
        platforms=["doubao", "deepseek"],
    )

    assert job.total_items == 4
    mock_reserve.assert_called_once()
    assert mock_reserve.call_args.kwargs["amount"] == 4

    added = [c.args[0] for c in db.add.call_args_list if isinstance(c.args[0], LLMResponse)]
    assert len(added) == 4
    assert [(row.prompt_id, row.platform) for row in added] == [
        (prompts[0].id, "doubao"),
        (prompts[1].id, "doubao"),
        (prompts[2].id, "doubao"),
        (prompts[0].id, "deepseek"),
    ]
    mock_enqueue.assert_called_once()
