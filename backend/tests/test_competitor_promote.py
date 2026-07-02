"""Tests for open-set brand promotion and signal migration."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

import pytest

from aperix_geo.db.models import Brand, Competitor, EntityKind, LLMResponseSignal, Subject, SubjectType
from aperix_geo.services.competitor.promote import (
    PromoteBrandError,
    backfill_competitor_signal_grid,
    migrate_open_brand_signals_to_competitor,
    promote_open_brand_to_competitor,
)


def _signal(**kwargs: object) -> LLMResponseSignal:
    defaults: dict[str, object] = {
        "id": uuid.uuid4(),
        "response_id": uuid.uuid4(),
        "subject_id": uuid.uuid4(),
        "prompt_id": uuid.uuid4(),
        "platform": "doubao",
        "entity_id": "other:stripe",
        "entity_kind": EntityKind.other.value,
        "brand_id": uuid.uuid4(),
        "entity_label": "Stripe",
        "primary_domain": "stripe.com",
        "mentioned": True,
        "mention_count": 1,
        "mention_rank": 1,
        "sentiment_score": 80.0,
        "sentiment_reason": "",
        "has_domain_link": False,
        "cited_on_source": False,
    }
    defaults.update(kwargs)
    return LLMResponseSignal(**defaults)


def test_migrate_open_brand_signals_rewrites_entity_fields() -> None:
    subject_id = uuid.uuid4()
    brand_id = uuid.uuid4()
    competitor_id = uuid.uuid4()
    signal = _signal(subject_id=subject_id, brand_id=brand_id)

    db = MagicMock()
    db.execute.side_effect = [
        MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[signal])))),
        MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))),
    ]

    migrated, dropped = migrate_open_brand_signals_to_competitor(
        db,
        subject_id=subject_id,
        brand_id=brand_id,
        competitor_id=competitor_id,
        entity_label="stripe.com",
    )

    assert migrated == 1
    assert dropped == 0
    assert signal.entity_id == str(competitor_id)
    assert signal.entity_kind == EntityKind.competitor.value
    assert signal.entity_label == "stripe.com"


def test_migrate_open_brand_signals_drops_conflicting_competitor_row() -> None:
    subject_id = uuid.uuid4()
    brand_id = uuid.uuid4()
    competitor_id = uuid.uuid4()
    response_id = uuid.uuid4()
    other = _signal(subject_id=subject_id, brand_id=brand_id, response_id=response_id)
    existing = _signal(
        subject_id=subject_id,
        brand_id=brand_id,
        response_id=response_id,
        entity_id=str(competitor_id),
        entity_kind=EntityKind.competitor.value,
    )

    db = MagicMock()
    db.execute.side_effect = [
        MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[other])))),
        MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[existing])))),
    ]

    migrated, dropped = migrate_open_brand_signals_to_competitor(
        db,
        subject_id=subject_id,
        brand_id=brand_id,
        competitor_id=competitor_id,
        entity_label="stripe.com",
    )

    assert migrated == 0
    assert dropped == 1
    db.delete.assert_called_once_with(other)


def test_backfill_competitor_signal_grid_adds_unmentioned_rows() -> None:
    from aperix_geo.services.analysis.entity import OWN_ENTITY_ID

    subject_id = uuid.uuid4()
    competitor_id = uuid.uuid4()
    brand_id = uuid.uuid4()
    response_a = uuid.uuid4()
    response_b = uuid.uuid4()
    own_a = _signal(
        subject_id=subject_id,
        response_id=response_a,
        entity_id=OWN_ENTITY_ID,
        entity_kind=EntityKind.own.value,
        mentioned=True,
    )
    own_b = _signal(
        subject_id=subject_id,
        response_id=response_b,
        entity_id=OWN_ENTITY_ID,
        entity_kind=EntityKind.own.value,
        mentioned=False,
    )
    promoted = _signal(
        subject_id=subject_id,
        response_id=response_a,
        brand_id=brand_id,
        entity_id=str(competitor_id),
        entity_kind=EntityKind.competitor.value,
        mentioned=True,
    )

    db = MagicMock()
    db.execute.return_value.scalars.return_value.all.return_value = [own_a, own_b, promoted]

    created = backfill_competitor_signal_grid(
        db,
        subject_id=subject_id,
        competitor_id=competitor_id,
        brand_id=brand_id,
        entity_label="stripe.com",
        primary_domain="stripe.com",
    )

    assert created == 1
    db.add.assert_called_once()
    db.flush.assert_called_once()
    row = db.add.call_args.args[0]
    assert row.response_id == response_b
    assert row.entity_id == str(competitor_id)
    assert row.mentioned is False
    assert row.mention_count == 0


def test_backfill_skips_when_migrated_row_still_in_session() -> None:
    """After migrate (pre-flush), sibling grid already carries competitor entity_id."""
    from aperix_geo.services.analysis.entity import OWN_ENTITY_ID

    subject_id = uuid.uuid4()
    competitor_id = uuid.uuid4()
    brand_id = uuid.uuid4()
    response_id = uuid.uuid4()
    own = _signal(
        subject_id=subject_id,
        response_id=response_id,
        entity_id=OWN_ENTITY_ID,
        entity_kind=EntityKind.own.value,
        mentioned=True,
    )
    migrated = _signal(
        subject_id=subject_id,
        response_id=response_id,
        brand_id=brand_id,
        entity_id=str(competitor_id),
        entity_kind=EntityKind.competitor.value,
        mentioned=True,
    )

    db = MagicMock()
    db.execute.return_value.scalars.return_value.all.return_value = [own, migrated]

    created = backfill_competitor_signal_grid(
        db,
        subject_id=subject_id,
        competitor_id=competitor_id,
        brand_id=brand_id,
        entity_label="openi.cn",
        primary_domain="openi.cn",
    )

    assert created == 0
    db.add.assert_not_called()
    db.flush.assert_not_called()


def _subject_with_brand() -> tuple[Subject, Brand]:
    subject_id = uuid.uuid4()
    subject = Subject(
        id=subject_id,
        tenant_id=uuid.uuid4(),
        type=SubjectType.domain,
        domain="aperix.com",
        brand="Aperix",
        website_url="https://aperix.com",
    )
    subject.competitors = []
    brand = Brand(
        id=uuid.uuid4(),
        subject_id=subject_id,
        entity_kind=EntityKind.other.value,
        brand="Stripe",
        domain="stripe.com",
        website_url="https://stripe.com",
        aliases=["斯特里普"],
        summary="支付",
        source="sampling_open_set",
    )
    return subject, brand


@patch("aperix_geo.services.competitor.promote.assert_competitor_capacity")
@patch("aperix_geo.services.competitor.promote.backfill_competitor_signal_grid", return_value=2)
@patch("aperix_geo.services.competitor.promote.migrate_open_brand_signals_to_competitor", return_value=(3, 1))
def test_promote_open_brand_to_competitor_creates_competitor_and_updates_brand(
    _mock_migrate: MagicMock,
    _mock_backfill: MagicMock,
    _mock_capacity: MagicMock,
) -> None:
    subject, brand = _subject_with_brand()
    db = MagicMock()
    db.execute.return_value.scalar_one_or_none.return_value = brand

    result = promote_open_brand_to_competitor(db, subject=subject, brand_id=brand.id)

    assert len(subject.competitors) == 1
    competitor = result.competitor
    assert isinstance(competitor, Competitor)
    assert competitor.brand == "Stripe"
    assert competitor.domain == "stripe.com"
    assert brand.entity_kind == EntityKind.competitor.value
    assert brand.entity_id == str(competitor.id)
    assert result.signals_migrated == 3
    assert result.signals_dropped == 1
    db.flush.assert_called()


def test_promote_open_brand_rejects_non_other() -> None:
    subject, brand = _subject_with_brand()
    brand.entity_kind = EntityKind.competitor.value
    db = MagicMock()
    db.execute.return_value.scalar_one_or_none.return_value = brand

    with pytest.raises(PromoteBrandError, match="开集"):
        promote_open_brand_to_competitor(db, subject=subject, brand_id=brand.id)


def test_promote_open_brand_rejects_duplicate_domain() -> None:
    subject, brand = _subject_with_brand()
    subject.competitors = [
        Competitor(
            id=uuid.uuid4(),
            subject_id=subject.id,
            brand="Wise",
            domain="stripe.com",
        )
    ]
    db = MagicMock()
    db.execute.return_value.scalar_one_or_none.return_value = brand

    with pytest.raises(PromoteBrandError, match="已是配置竞品"):
        promote_open_brand_to_competitor(db, subject=subject, brand_id=brand.id)
