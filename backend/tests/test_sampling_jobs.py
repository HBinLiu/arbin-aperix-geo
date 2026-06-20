"""Tests for sampling job creation guards."""

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from aperix_geo.db.models import Prompt, Subject, SubjectType
from aperix_geo.services.sampling.workflow.jobs import SamplingJobError, create_and_enqueue_sampling_job


def _subject() -> Subject:
    return Subject(
        id=uuid4(),
        tenant_id=uuid4(),
        type=SubjectType.brand,
        brand="Aperix",
        website_url="https://aperix.com",
    )


def _prompt(subject: Subject) -> Prompt:
    return Prompt(
        id=uuid4(),
        subject_id=subject.id,
        text="test prompt",
        text_hash="hash",
        enabled=True,
    )


def _mock_db(subject: Subject, prompt: Prompt) -> MagicMock:
    db = MagicMock()
    prompt_result = MagicMock()
    prompt_result.scalars.return_value.all.return_value = [prompt]
    subject_result = MagicMock()
    subject_result.scalar_one_or_none.return_value = subject
    db.execute.side_effect = [prompt_result, subject_result]
    return db


@patch("aperix_geo.services.sampling.workflow.orchestrate.enqueue_sampling_orchestration")
@patch("aperix_geo.services.sampling.workflow.jobs.subject_has_active_sampling_job", return_value=False)
def test_create_sampling_job_locks_subject_and_succeeds(
    _mock_active: MagicMock,
    mock_enqueue: MagicMock,
) -> None:
    subject = _subject()
    prompt = _prompt(subject)
    db = _mock_db(subject, prompt)

    job = create_and_enqueue_sampling_job(
        db,
        subject=subject,
        tenant_id=subject.tenant_id,
        platforms=["doubao"],
    )

    assert job.total_items == 1
    db.commit.assert_called_once()
    mock_enqueue.assert_called_once()


@patch("aperix_geo.services.sampling.workflow.jobs.subject_has_active_sampling_job", return_value=True)
def test_create_sampling_job_rejects_active_job(_mock_active: MagicMock) -> None:
    subject = _subject()
    prompt = _prompt(subject)
    db = _mock_db(subject, prompt)

    with pytest.raises(SamplingJobError, match="already queued or running"):
        create_and_enqueue_sampling_job(
            db,
            subject=subject,
            tenant_id=subject.tenant_id,
            platforms=["doubao"],
        )

    db.commit.assert_not_called()
