"""Tests for sampling open-set brand persistence."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

from aperix_geo.db.models import BrandSource, Competitor, Subject, SubjectType
from aperix_geo.services.competitor.types import SiteHead
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
        patch("aperix_geo.services.sampling.brand.enrich_open_set_brand_aliases", return_value=[]),
        patch("aperix_geo.services.sampling.brand.resolve_or_create_brand") as upsert,
    ):
        catalog = MagicMock()
        catalog.find_by_name_or_alias.return_value = None
        load_ctx.return_value = MagicMock(catalog=catalog)
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


def test_persist_open_brands_merges_alias_when_domain_verified() -> None:
    db = MagicMock()
    subject = _subject()
    subject.competitors = []
    absa = {
        "other_brands_sentiment_absa": {
            "TransferWise": {"mentioned": True, "score": 70, "evidence": "TransferWise"},
        }
    }
    existing = MagicMock()
    existing.entity_kind = "other"
    existing.brand = "Wise"
    existing.aliases = []
    existing.domain = "wise.com"

    catalog = MagicMock()
    catalog.find_by_name_or_alias.return_value = None
    catalog.find_by_domain.return_value = existing

    wise_head = SiteHead(
        "wise.com",
        "Wise | TransferWise",
        "",
        True,
        brand_names=("TransferWise",),
    )

    with (
        patch("aperix_geo.services.sampling.brand.BrandSyncContext.load") as load_ctx,
        patch(
            "aperix_geo.services.sampling.brand.extract_domain_from_text_for_brand",
            return_value="wise.com",
        ),
        patch("aperix_geo.services.sampling.brand.fetch_site_heads", return_value={"wise.com": wise_head}),
        patch("aperix_geo.services.sampling.brand.remember_brand_row_domains") as remember,
        patch("aperix_geo.services.sampling.brand.resolve_or_create_brand") as upsert,
    ):
        load_ctx.return_value = MagicMock(catalog=catalog)
        count = persist_open_brands_from_absa(
            db,
            subject=subject,
            response_absa=absa,
            raw_text="推荐 TransferWise",
            url_hosts=["wise.com"],
        )

    assert count == 1
    upsert.assert_not_called()
    remember.assert_called_once()
    assert "TransferWise" in existing.aliases


def test_persist_open_brands_skips_competitor_alias() -> None:
    db = MagicMock()
    subject = _subject()
    subject.competitors[0].aliases = ["贝塔科技"]
    absa = {
        "other_brands_sentiment_absa": {
            "贝塔科技": {"mentioned": True, "score": 60, "evidence": "贝塔科技"},
        }
    }

    with patch("aperix_geo.services.sampling.brand.resolve_or_create_brand") as upsert:
        count = persist_open_brands_from_absa(
            db,
            subject=subject,
            response_absa=absa,
            raw_text="推荐贝塔科技",
            url_hosts=[],
        )

    assert count == 0
    upsert.assert_not_called()


def test_persist_open_brands_skips_existing_tb_brands_alias() -> None:
    db = MagicMock()
    subject = _subject()
    absa = {
        "other_brands_sentiment_absa": {
            "TransferWise": {"mentioned": True, "score": 70, "evidence": "TransferWise"},
        }
    }
    existing_brand = MagicMock()
    catalog = MagicMock()
    catalog.find_by_name_or_alias = MagicMock(return_value=existing_brand)

    with (
        patch("aperix_geo.services.sampling.brand.BrandSyncContext.load") as load_ctx,
        patch("aperix_geo.services.sampling.brand.resolve_or_create_brand") as upsert,
    ):
        load_ctx.return_value = MagicMock(catalog=catalog)
        count = persist_open_brands_from_absa(
            db,
            subject=subject,
            response_absa=absa,
            raw_text="TransferWise 跨境汇款",
            url_hosts=[],
        )

    catalog.find_by_name_or_alias.assert_called_once_with("TransferWise")
    assert count == 0
    upsert.assert_not_called()


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
