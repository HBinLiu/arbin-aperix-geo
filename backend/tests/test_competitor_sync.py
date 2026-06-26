"""Tests for competitor signal reconciliation on delete."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

from aperix_geo.db.models import Brand, EntityKind, LLMResponseSignal
from aperix_geo.services.competitor.reconcile import demote_competitor_signals


def test_demote_competitor_signals_reverts_to_open_set() -> None:
    subject_id = uuid.uuid4()
    competitor_id = uuid.uuid4()
    brand_id = uuid.uuid4()
    brand = Brand(
        id=brand_id,
        subject_id=subject_id,
        entity_kind=EntityKind.competitor.value,
        brand="Gamma",
        domain="gamma.com",
    )
    signal = LLMResponseSignal(
        id=uuid.uuid4(),
        response_id=uuid.uuid4(),
        subject_id=subject_id,
        prompt_id=uuid.uuid4(),
        platform="doubao",
        entity_id=str(competitor_id),
        entity_kind=EntityKind.competitor.value,
        brand_id=brand_id,
        entity_label="gamma.com",
        mentioned=True,
        mention_count=1,
        mention_rank=1,
        sentiment_score=70.0,
        sentiment_reason="",
        has_domain_link=False,
        cited_on_source=False,
    )

    db = MagicMock()
    db.execute.return_value.scalars.return_value.all.return_value = [signal]
    db.get.return_value = brand

    with patch(
        "aperix_geo.services.competitor.reconcile.find_brand_by_entity_id",
        return_value=brand,
    ):
        count = demote_competitor_signals(
            db,
            subject_id=subject_id,
            competitor_id=competitor_id,
        )

    assert count == 1
    assert brand.entity_kind == EntityKind.other.value
    assert brand.entity_id == ""
    assert signal.entity_kind == EntityKind.other.value
    assert signal.entity_id.startswith("other:")
    assert signal.entity_label == "gamma.com"


def test_demote_competitor_clears_brand_entity_id_without_signals() -> None:
    subject_id = uuid.uuid4()
    competitor_id = uuid.uuid4()
    brand = Brand(
        id=uuid.uuid4(),
        subject_id=subject_id,
        entity_kind=EntityKind.competitor.value,
        entity_id=str(competitor_id),
        brand="Gamma",
        domain="gamma.com",
    )

    db = MagicMock()
    db.execute.return_value.scalars.return_value.all.return_value = []

    with patch(
        "aperix_geo.services.competitor.reconcile.find_brand_by_entity_id",
        return_value=brand,
    ):
        count = demote_competitor_signals(
            db,
            subject_id=subject_id,
            competitor_id=competitor_id,
        )

    assert count == 0
    assert brand.entity_kind == EntityKind.other.value
    assert brand.entity_id == ""
