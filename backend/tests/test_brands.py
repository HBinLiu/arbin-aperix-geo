"""Tests for tenant-scoped tb_brands resolve/upsert."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from aperix_geo.db.models import EntityKind
from aperix_geo.services.brand.resolve import normalize_brand_key, primary_domain_for_brand
from aperix_geo.services.sampling.signal_draft import EntitySignalDraft
from aperix_geo.services.sampling.signals import build_llm_response_signal_rows


@dataclass
class _FakeBrand:
    id: uuid.UUID
    domain: str


def test_normalize_brand_key() -> None:
    assert normalize_brand_key("  Stripe ") == "stripe"
    assert normalize_brand_key("阿里健康") == "阿里健康"


def test_primary_domain_for_brand_normalizes_host() -> None:
    brand = _FakeBrand(id=uuid.uuid4(), domain="aperix.com")
    assert primary_domain_for_brand(brand) == "aperix.com"  # type: ignore[arg-type]


def test_build_signal_rows_include_brand_fields() -> None:
    brand_id = uuid.uuid4()
    brand = _FakeBrand(id=brand_id, domain="aperix.com")
    draft = EntitySignalDraft(
        entity_id="own",
        entity_kind=EntityKind.own.value,
        entity_label="aperix.com",
        mentioned=True,
        mention_count=1,
        sentiment_score=80.0,
        sentiment_reason="推荐",
    )
    rows = build_llm_response_signal_rows(
        response_id=uuid.uuid4(),
        subject_id=uuid.uuid4(),
        prompt_id=uuid.uuid4(),
        platform="doubao",
        created_at=datetime.now(UTC),
        entity_signals=[draft],
        brands_by_entity_id={"own": brand},  # type: ignore[arg-type]
    )
    assert len(rows) == 1
    assert rows[0].brand_id == brand_id
    assert rows[0].entity_label == "aperix.com"
    assert rows[0].primary_domain == "aperix.com"
