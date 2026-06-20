"""Tests for open-set competitive brand filtering."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

from aperix_geo.db.models import Brand, Competitor, Subject, SubjectType
from aperix_geo.services.competitor.types import CompetitorScore, CrossValidateResult
from aperix_geo.services.sampling.filter import filter_competitive_other_brands


def _subject() -> Subject:
    subject_id = uuid.uuid4()
    subject = Subject(
        id=subject_id,
        tenant_id=uuid.uuid4(),
        type=SubjectType.domain,
        domain="aperix.com",
        brand="Aperix",
        website_url="https://aperix.com",
        niche_profile={
            "company": "Aperix",
            "industry": "GEO SaaS",
            "features": "监测",
            "customers": "品牌",
            "keywords": "AI搜索",
        },
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


@patch("aperix_geo.services.sampling.filter.resolve_or_create_brand")
@patch("aperix_geo.services.sampling.filter.find_brand_by_name_or_alias", return_value=None)
@patch("aperix_geo.services.sampling.filter.get_settings")
@patch("aperix_geo.services.sampling.filter.run_cross_validate")
def test_filter_batches_cross_validate(
    mock_validate: MagicMock,
    mock_settings: MagicMock,
    _mock_find: MagicMock,
    _mock_resolve: MagicMock,
) -> None:
    mock_settings.return_value.competitor_cross_validate_pass_score = 6.0
    mock_validate.return_value = CrossValidateResult(
        scores=[
            CompetitorScore(domain="stripe.com", score=8.0, reason="同类支付"),
            CompetitorScore(domain="wise.com", score=3.0, reason="弱相关"),
        ],
        heads={},
    )

    subject = _subject()
    db = MagicMock()

    others = {
        "Stripe": {"mentioned": True, "score": 80},
        "Wise": {"mentioned": True, "score": 60},
        "Beta": {"mentioned": True, "score": 50},
        "Aperix": {"mentioned": True, "score": 90},
    }
    text = "推荐 Stripe 与 Wise"

    with patch(
        "aperix_geo.services.sampling.filter.extract_domain_from_text_for_brand",
        side_effect=lambda _text, label, _urls: {
            "Stripe": "stripe.com",
            "Wise": "wise.com",
        }.get(label),
    ):
        kept = filter_competitive_other_brands(
            db,
            subject=subject,
            others=others,
            raw_text=text,
            url_hosts=["stripe.com", "wise.com"],
        )

    assert set(kept.keys()) == {"Stripe"}
    mock_validate.assert_called_once()
    pool = mock_validate.call_args.kwargs["pool"]
    assert set(pool.domains) == {"stripe.com", "wise.com"}


@patch("aperix_geo.services.sampling.filter.get_settings")
def test_filter_reuses_stored_cross_validate_score(mock_settings: MagicMock) -> None:
    mock_settings.return_value.competitor_cross_validate_pass_score = 6.0
    subject = _subject()
    db = MagicMock()

    existing = Brand(
        id=uuid.uuid4(),
        subject_id=subject.id,
        brand="Stripe",
        domain="stripe.com",
        entity_kind="other",
        cross_validate_score=7.5,
    )

    with patch(
        "aperix_geo.services.sampling.filter.find_brand_by_name_or_alias",
        return_value=existing,
    ):
        with patch(
            "aperix_geo.services.sampling.filter.run_cross_validate",
        ) as mock_validate:
            kept = filter_competitive_other_brands(
                db,
                subject=subject,
                others={"Stripe": {"mentioned": True, "score": 80}},
                raw_text="推荐 Stripe https://stripe.com",
            )

    assert "Stripe" in kept
    mock_validate.assert_not_called()


@patch("aperix_geo.services.sampling.filter.get_settings")
def test_filter_drops_stored_score_below_threshold(mock_settings: MagicMock) -> None:
    mock_settings.return_value.competitor_cross_validate_pass_score = 6.0
    subject = _subject()
    db = MagicMock()

    existing = Brand(
        id=uuid.uuid4(),
        subject_id=subject.id,
        brand="Stripe",
        domain="stripe.com",
        entity_kind="other",
        cross_validate_score=4.0,
    )

    with patch(
        "aperix_geo.services.sampling.filter.find_brand_by_name_or_alias",
        return_value=existing,
    ):
        kept = filter_competitive_other_brands(
            db,
            subject=subject,
            others={"Stripe": {"mentioned": True, "score": 80}},
            raw_text="推荐 Stripe https://stripe.com",
        )

    assert kept == {}


@patch("aperix_geo.services.sampling.filter.resolve_or_create_brand")
@patch("aperix_geo.services.sampling.filter.find_brand_by_name_or_alias", return_value=None)
@patch("aperix_geo.services.sampling.filter.get_settings")
@patch("aperix_geo.services.sampling.filter.run_cross_validate")
def test_filter_reuses_redis_cross_validate_cache(
    mock_validate: MagicMock,
    mock_settings: MagicMock,
    _mock_find: MagicMock,
    _mock_resolve: MagicMock,
) -> None:
    from aperix_geo.services.sampling.cache.cross_validate import (
        clear_cross_validate_score_cache,
        set_cross_validate_score_cached,
    )

    clear_cross_validate_score_cache()
    mock_settings.return_value.competitor_cross_validate_pass_score = 6.0
    subject = _subject()
    db = MagicMock()
    set_cross_validate_score_cached(
        subject_id=subject.id,
        domain="wise.com",
        score=3.0,
        reason="弱相关",
    )

    others = {
        "Stripe": {"mentioned": True, "score": 80},
        "Wise": {"mentioned": True, "score": 60},
    }
    text = "推荐 Stripe 与 Wise"

    with patch(
        "aperix_geo.services.sampling.filter.extract_domain_from_text_for_brand",
        side_effect=lambda _text, label, _urls: {
            "Stripe": "stripe.com",
            "Wise": "wise.com",
        }.get(label),
    ):
        mock_validate.return_value = CrossValidateResult(
            scores=[CompetitorScore(domain="stripe.com", score=8.0, reason="同类支付")],
            heads={},
        )
        kept = filter_competitive_other_brands(
            db,
            subject=subject,
            others=others,
            raw_text=text,
            url_hosts=["stripe.com", "wise.com"],
        )

    assert set(kept.keys()) == {"Stripe"}
    mock_validate.assert_called_once()
    pool = mock_validate.call_args.kwargs["pool"]
    assert set(pool.domains) == {"stripe.com"}
