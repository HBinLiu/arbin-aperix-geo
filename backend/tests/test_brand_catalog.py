"""Tests for subject brand catalog and alias lookup."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

from aperix_geo.db.models import Brand
from aperix_geo.services.brand.catalog import BrandCatalog, BrandSyncContext
from aperix_geo.services.brand.domain import resolve_brand_domain
from aperix_geo.services.brand.resolve import find_brand_by_name_or_alias


def _brand(*, brand: str, domain: str = "", aliases: list[str] | None = None) -> Brand:
    return Brand(
        id=uuid.uuid4(),
        subject_id=uuid.uuid4(),
        entity_kind="other",
        brand=brand,
        domain=domain,
        website_url="",
        aliases=aliases or [],
        summary="",
    )


def test_brand_catalog_indexes_name_alias_and_domain() -> None:
    row = _brand(brand="Stripe", domain="stripe.com", aliases=["斯特里普"])
    catalog = BrandCatalog()
    catalog.register(row)

    assert catalog.find_by_name_or_alias("Stripe") is row
    assert catalog.find_by_name_or_alias("stripe") is row
    assert catalog.find_by_name_or_alias("斯特里普") is row
    assert catalog.find_by_canonical_name("Stripe") is row
    assert catalog.find_by_canonical_name("斯特里普") is None
    assert catalog.find_by_domain("stripe.com") is row
    assert catalog.find_by_name_or_alias("PayPal") is None


def test_brand_sync_context_memoizes_domain() -> None:
    ctx = BrandSyncContext(catalog=BrandCatalog())
    ctx.remember_domain("Stripe", "stripe.com")

    assert ctx.memoized_domain("stripe") == "stripe.com"
    assert ctx.memoized_domain("Stripe") == "stripe.com"


def test_find_brand_by_name_or_alias_scans_aliases() -> None:
    subject_id = uuid.uuid4()
    row = _brand(brand="Stripe", domain="stripe.com", aliases=["斯特里普"])
    db = MagicMock()
    name_result = MagicMock()
    name_result.scalar_one_or_none.return_value = None
    list_result = MagicMock()
    list_result.scalars.return_value = iter([row])
    db.execute.side_effect = [name_result, list_result]

    found = find_brand_by_name_or_alias(db, subject_id=subject_id, brand="斯特里普")
    assert found is row


@patch("aperix_geo.services.brand.domain.search_brand_official_domain")
@patch("aperix_geo.services.brand.domain.extract_domain_from_text_for_brand")
def test_resolve_brand_domain_uses_catalog_alias_hit(mock_extract, mock_search) -> None:
    row = _brand(brand="Stripe", domain="stripe.com", aliases=["斯特里普"])
    catalog = BrandCatalog()
    catalog.register(row)
    ctx = BrandSyncContext(catalog=catalog)

    domain = resolve_brand_domain(
        MagicMock(),
        subject_id=uuid.uuid4(),
        brand="斯特里普",
        sync_ctx=ctx,
    )

    assert domain == "stripe.com"
    mock_extract.assert_not_called()
    mock_search.assert_not_called()
    assert ctx.memoized_domain("斯特里普") == "stripe.com"


@patch("aperix_geo.services.brand.domain.search_brand_official_domain")
@patch("aperix_geo.services.brand.domain.extract_domain_from_text_for_brand")
def test_resolve_brand_domain_reuses_batch_domain_memo(mock_extract, mock_search) -> None:
    ctx = BrandSyncContext(catalog=BrandCatalog())
    ctx.remember_domain("Stripe", "stripe.com")

    domain = resolve_brand_domain(
        MagicMock(),
        subject_id=uuid.uuid4(),
        brand="Stripe",
        sync_ctx=ctx,
    )

    assert domain == "stripe.com"
    mock_extract.assert_not_called()
    mock_search.assert_not_called()


@patch("aperix_geo.services.brand.domain.get_brand_domain_cached", return_value=None)
@patch("aperix_geo.services.brand.resolve.find_brand_by_name_or_alias", return_value=None)
@patch("aperix_geo.services.brand.domain._verified_domain", return_value="")
@patch("aperix_geo.services.brand.domain.search_brand_official_domain", return_value="")
@patch("aperix_geo.services.brand.domain.extract_domain_from_text_for_brand", return_value="stripe.com")
def test_resolve_brand_domain_skips_unresolvable_discovered_domain(
    mock_extract,
    mock_search,
    _mock_verified,
    _mock_find,
    _mock_cache,
) -> None:
    domain = resolve_brand_domain(
        MagicMock(),
        subject_id=uuid.uuid4(),
        brand="Stripe",
        raw_text="see https://stripe.com",
    )

    assert domain == ""
    mock_extract.assert_called_once()
    mock_search.assert_called_once()


@patch("aperix_geo.services.brand.domain.get_brand_domain_cached", return_value=None)
@patch("aperix_geo.services.brand.resolve.find_brand_by_name_or_alias", return_value=None)
@patch("aperix_geo.services.brand.domain._verified_domain", return_value="stripe.com")
@patch("aperix_geo.services.brand.domain.search_brand_official_domain")
@patch("aperix_geo.services.brand.domain.extract_domain_from_text_for_brand", return_value="stripe.com")
def test_resolve_brand_domain_persists_resolvable_text_domain(
    mock_extract,
    mock_search,
    _mock_verified,
    _mock_find,
    _mock_cache,
) -> None:
    domain = resolve_brand_domain(
        MagicMock(),
        subject_id=uuid.uuid4(),
        brand="Stripe",
        raw_text="see https://stripe.com",
    )

    assert domain == "stripe.com"
    mock_extract.assert_called_once()
    mock_search.assert_not_called()
