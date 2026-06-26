"""Tests for brand opportunity aggregation."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from aperix_geo.db.models import Brand, EntityKind, Subject, SubjectType
from aperix_geo.services.analysis.brand import build_brands


def _subject() -> Subject:
    return Subject(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        type=SubjectType.brand,
        brand="Aperix",
        website_url="https://aperix.com",
        domain="aperix.com",
    )


def test_build_brands_returns_page_payload() -> None:
    subject = _subject()
    db = MagicMock()
    brand_id = uuid.uuid4()
    items = [
        {
            "brand_id": str(brand_id),
            "label": "Stripe",
            "display_name": "Stripe",
            "domain": "stripe.com",
            "response_count": 4,
            "visibility_rate": 0.75,
            "mention_rate": 1.0,
            "share_voice": 0.25,
            "average_rank": 2.0,
            "citation_rate": 0.5,
            "sentiment_score": 72.0,
            "sentiment_label": "positive",
            "citation_coverage": None,
        }
    ]

    with patch(
        "aperix_geo.services.analysis.brand.query_brands_page",
        return_value=(items, 1),
    ) as query_mock:
        result = build_brands(
            db,
            subject=subject,
            dt_from=datetime(2026, 1, 1, tzinfo=UTC),
            dt_to=datetime(2026, 1, 31, tzinfo=UTC),
            page=2,
            page_size=5,
        )

    query_mock.assert_called_once()
    assert result["items"] == items
    assert result["total"] == 1
    assert result["page"] == 2
    assert result["page_size"] == 5


def test_open_brand_metrics_subquery_filters_other_kind() -> None:
    from aperix_geo.services.analysis.brand_sql import _open_brand_signal_filters

    subject_id = uuid.uuid4()
    filters = _open_brand_signal_filters(
        subject_id=subject_id,
        dt_from=datetime(2026, 1, 1, tzinfo=UTC),
        dt_to=datetime(2026, 1, 31, tzinfo=UTC),
        platform=["doubao"],
        topic_id=[uuid.uuid4()],
    )
    assert any(
        getattr(getattr(item, "left", None), "key", None) == "entity_kind"
        or str(item).endswith("entity_kind")
        for item in filters
    )


def test_metrics_bundle_for_open_brand_uses_window_denominator() -> None:
    from types import SimpleNamespace

    from aperix_geo.services.analysis.brand_sql import metrics_bundle_for_open_brand

    subject = _subject()
    row = SimpleNamespace(
        mentioned_responses=2,
        mention_total=3,
        mention_with_link=1,
        cited_on_source_rows=0,
        avg_rank=2.5,
        sentiment_avg=70.0,
    )
    metrics = metrics_bundle_for_open_brand(
        row,
        subject=subject,
        total_voice=10,
        window_response_total=10,
    )
    assert metrics.response_count == 10
    assert metrics.visibility_rate == 0.2
    assert metrics.mention_rate == 0.3
    assert metrics.share_voice == 0.3
    assert metrics.citation_rate == 0.5


def test_brand_entity_kind_other_constant() -> None:
    brand = Brand(
        id=uuid.uuid4(),
        subject_id=uuid.uuid4(),
        entity_kind=EntityKind.other.value,
        brand="Stripe",
        domain="stripe.com",
    )
    assert brand.entity_kind == "other"
