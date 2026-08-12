"""Tests for single-row competitor add/remove."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

import pytest

from aperix_geo.db.models import Competitor, Subject, SubjectType
from aperix_geo.schemas.catalog import CompetitorItem
from aperix_geo.services.billing.exceptions import QuotaExceededError
from aperix_geo.services.competitor.persist import (
    DuplicateCompetitorError,
    InvalidCompetitorError,
    CompetitorNotFoundError,
    add_competitor,
    remove_competitor_by_id,
    update_competitor_by_id,
)


@pytest.fixture(autouse=True)
def _skip_competitor_quota_check() -> None:
    with patch("aperix_geo.services.competitor.persist.assert_competitor_capacity"):
        yield


def _domain_subject(*, competitors: list[Competitor] | None = None) -> Subject:
    subject = Subject(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        type=SubjectType.domain,
        brand="Aperix",
        website_url="https://aperix.com",
        domain="aperix.com",
    )
    subject.competitors = list(competitors or [])
    return subject


def test_add_competitor_appends_new_row() -> None:
    subject = _domain_subject()
    db = MagicMock()

    competitor = add_competitor(
        db,
        subject,
        item=CompetitorItem(domain="beta.com", website_url="https://beta.com", brand="Beta"),
    )

    assert len(subject.competitors) == 1
    assert competitor.domain == "beta.com"
    assert competitor.brand == "Beta"
    db.flush.assert_called_once()


def test_add_competitor_rejects_duplicate_domain() -> None:
    existing = Competitor(
        id=uuid.uuid4(),
        subject_id=uuid.uuid4(),
        domain="beta.com",
        website_url="https://beta.com",
        brand="Beta",
    )
    subject = _domain_subject(competitors=[existing])
    db = MagicMock()

    with pytest.raises(DuplicateCompetitorError):
        add_competitor(
            db,
            subject,
            item=CompetitorItem(domain="beta.com", website_url="https://beta.com", brand="Beta"),
        )


def test_add_competitor_rejects_invalid_fields() -> None:
    subject = _domain_subject()
    db = MagicMock()

    with pytest.raises(InvalidCompetitorError):
        add_competitor(db, subject, item=CompetitorItem(domain="x", brand=""))


@patch(
    "aperix_geo.services.competitor.persist.assert_competitor_capacity",
    side_effect=QuotaExceededError(dimension="max_per_competitors"),
)
def test_add_competitor_enforces_limit(_mock_assert: MagicMock) -> None:
    subject = _domain_subject()
    db = MagicMock()

    with pytest.raises(QuotaExceededError):
        add_competitor(
            db,
            subject,
            item=CompetitorItem(domain="new.com", website_url="https://new.com", brand="New"),
        )


def test_remove_competitor_by_id_deletes_row() -> None:
    target_id = uuid.uuid4()
    target = Competitor(
        id=target_id,
        subject_id=uuid.uuid4(),
        domain="beta.com",
        website_url="https://beta.com",
        brand="Beta",
    )
    subject = _domain_subject(competitors=[target])
    db = MagicMock()

    removed_id = remove_competitor_by_id(db, subject, competitor_id=target_id)

    assert removed_id == target_id
    assert subject.competitors == []
    db.delete.assert_called_once_with(target)
    db.flush.assert_called_once()


def test_remove_competitor_by_id_missing_raises() -> None:
    subject = _domain_subject()
    db = MagicMock()

    with pytest.raises(CompetitorNotFoundError):
        remove_competitor_by_id(db, subject, competitor_id=uuid.uuid4())


def test_update_competitor_by_id_preserves_id_and_updates_fields() -> None:
    target_id = uuid.uuid4()
    target = Competitor(
        id=target_id,
        subject_id=uuid.uuid4(),
        domain="beta.com",
        website_url="https://beta.com",
        brand="Beta",
        aliases=["B"],
        summary="old",
    )
    subject = _domain_subject(competitors=[target])
    db = MagicMock()

    updated = update_competitor_by_id(
        db,
        subject,
        competitor_id=target_id,
        item=CompetitorItem(
            domain="beta.com",
            website_url="https://beta.com",
            brand="Beta Corp",
            aliases=["B", "BetaCo"],
            summary="new summary",
        ),
    )

    assert updated.id == target_id
    assert updated.brand == "Beta Corp"
    assert updated.aliases == ["B", "BetaCo"]
    assert updated.summary == "new summary"
    assert db.flush.call_count >= 1


def test_update_competitor_by_id_rejects_duplicate_brand() -> None:
    a_id = uuid.uuid4()
    b_id = uuid.uuid4()
    subject = _domain_subject(
        competitors=[
            Competitor(
                id=a_id,
                subject_id=uuid.uuid4(),
                domain="",
                website_url="",
                brand="Alpha",
            ),
            Competitor(
                id=b_id,
                subject_id=uuid.uuid4(),
                domain="",
                website_url="",
                brand="Beta",
            ),
        ]
    )
    db = MagicMock()

    with pytest.raises(DuplicateCompetitorError):
        update_competitor_by_id(
            db,
            subject,
            competitor_id=a_id,
            item=CompetitorItem(domain="", website_url="", brand="Beta"),
        )
