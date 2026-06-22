"""Tests for sampling open-set brand persistence."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

from aperix_geo.db.models import BrandSource, Competitor, Subject, SubjectType
from aperix_geo.services.sampling.brand import persist_open_brands_from_absa


def _subject() -> Subject:
    subject_id = uuid.uuid4()
    subject = Subject(
        id=subject_id,
        tenant_id=uuid.uuid4(),
        type=SubjectType.brand,
        brand="Aperix",
        domain="aperix.com",
    )
    subject.competitors = [
        Competitor(
            id=uuid.uuid4(),
            subject_id=subject_id,
            brand="Beta",
            domain="beta.com",
        )
    ]
    return subject


def test_persist_open_brands_creates_rows_without_cross_validate() -> None:
    db = MagicMock()
    subject = _subject()
    absa = {
        "other_brands_sentiment_absa": {
            "Stripe": {"mentioned": True, "score": 75, "evidence": "Stripe"},
            "Beta": {"mentioned": True, "score": 60, "evidence": "Beta"},
        }
    }

    with (
        patch(
            "aperix_geo.services.sampling.brand.extract_domain_from_text_for_brand",
            side_effect=lambda _text, brand, _urls: "stripe.com" if brand == "Stripe" else "",
        ),
        patch("aperix_geo.services.sampling.brand.resolve_brand_domain", return_value=""),
        patch("aperix_geo.services.sampling.brand.BrandSyncContext.load") as load_ctx,
        patch("aperix_geo.services.sampling.brand.resolve_or_create_brand") as upsert,
    ):
        load_ctx.return_value = MagicMock(catalog=MagicMock())
        count = persist_open_brands_from_absa(
            db,
            subject=subject,
            response_absa=absa,
            raw_text="推荐 Stripe 与 Beta",
            url_hosts=["stripe.com"],
        )

    assert count == 1
    upsert.assert_called_once()
    kwargs = upsert.call_args.kwargs
    assert kwargs["brand"] == "Stripe"
    assert kwargs["domain"] == "stripe.com"
    assert kwargs["entity_kind"] == "other"
    assert kwargs["source"] == BrandSource.sampling_open_set
    db.flush.assert_called_once()


def test_persist_open_brands_skips_unmentioned_and_closed_set() -> None:
    db = MagicMock()
    subject = _subject()
    absa = {
        "other_brands_sentiment_absa": {
            "Aperix": {"mentioned": True, "score": 80, "evidence": "Aperix"},
            "Ghost": {"mentioned": False, "score": None, "evidence": ""},
        }
    }

    with patch("aperix_geo.services.sampling.brand.resolve_or_create_brand") as upsert:
        count = persist_open_brands_from_absa(
            db,
            subject=subject,
            response_absa=absa,
            raw_text="Aperix only",
            url_hosts=[],
        )

    assert count == 0
    upsert.assert_not_called()
    db.flush.assert_not_called()
