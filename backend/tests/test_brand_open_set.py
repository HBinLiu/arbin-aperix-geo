"""Tests for open-set brand resolve behavior."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

from aperix_geo.db.models import Brand
from aperix_geo.services.brand.catalog import BrandCatalog
from aperix_geo.services.brand.resolve import resolve_or_create_brand


def test_open_set_brand_does_not_merge_by_shared_citation_domain() -> None:
    subject_id = uuid.uuid4()
    existing = Brand(
        id=uuid.uuid4(),
        subject_id=subject_id,
        entity_kind="other",
        brand="透镜GEO",
        domain="zgswcn.com",
        website_url="",
        aliases=[],
        summary="",
    )
    catalog = BrandCatalog()
    catalog.register(existing)

    db = MagicMock()
    name_result = MagicMock()
    name_result.scalar_one_or_none.return_value = None
    db.execute.return_value = name_result
    db.add = MagicMock()
    db.begin_nested = MagicMock(
        return_value=MagicMock(__enter__=lambda s: s, __exit__=lambda s, *a: None)
    )
    db.flush = MagicMock()

    with patch("aperix_geo.services.brand.resolve.remember_brand_row_domains"):
        created = resolve_or_create_brand(
            db,
            subject_id=subject_id,
            brand="智瞰引擎",
            domain="zgswcn.com",
            entity_kind="other",
            catalog=catalog,
            open_set_brand=True,
        )

    assert created.brand == "智瞰引擎"
    assert created.id != existing.id
    db.add.assert_called_once()
