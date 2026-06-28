"""Tests for usage pack catalog."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock

from aperix_geo.db.models import PlanPack
from aperix_geo.services.billing.usage_pack_catalog import get_usage_pack_catalog


def test_get_usage_pack_catalog_excludes_custom_and_formats_items() -> None:
    packs = [
        PlanPack(
            id=uuid.uuid4(),
            code="pack_1000",
            quantity=1000,
            price_cents=12900,
            unit_price_cents=13,
            min_quantity=100,
            is_active=True,
            sort_order=1,
            deleted=False,
        ),
        PlanPack(
            id=uuid.uuid4(),
            code="custom",
            quantity=0,
            price_cents=0,
            unit_price_cents=15,
            min_quantity=100,
            is_active=True,
            sort_order=4,
            deleted=False,
        ),
    ]

    db = MagicMock()
    db.execute.return_value.scalars.return_value.all.return_value = [packs[0]]

    catalog = get_usage_pack_catalog(db)

    assert len(catalog.packs) == 1
    assert catalog.packs[0].code == "pack_1000"
    assert catalog.packs[0].title == "1,000 次"
    assert catalog.packs[0].order_label == "AI 配额包 1,000"
    assert catalog.packs[0].price_cents == 12900
