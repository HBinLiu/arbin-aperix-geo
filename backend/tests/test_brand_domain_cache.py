"""Tests for persistent brand domain Redis cache."""

from __future__ import annotations

import uuid
from unittest.mock import patch

from aperix_geo.db.models import Brand
from aperix_geo.services.brand.cache import (
    clear_brand_domain_cache,
    get_brand_domain_cached,
    remember_brand_domain_cached,
    remember_brand_row_domains,
)
from aperix_geo.services.brand.domain import resolve_brand_domain


def test_remember_and_get_brand_domain_cached() -> None:
    clear_brand_domain_cache()
    tenant_id = uuid.uuid4()
    with patch("aperix_geo.services.brand.cache.redis_set_json_persistent") as mock_set:
        with patch("aperix_geo.services.brand.cache.redis_get_json", return_value=None):
            remember_brand_domain_cached(tenant_id=tenant_id, brand="Stripe", domain="stripe.com")
            assert mock_set.called

    with patch(
        "aperix_geo.services.brand.cache.redis_get_json",
        return_value={"domain": "stripe.com"},
    ):
        assert get_brand_domain_cached(tenant_id=tenant_id, brand="stripe") == "stripe.com"


def test_remember_brand_row_domains_warms_aliases() -> None:
    clear_brand_domain_cache()
    tenant_id = uuid.uuid4()
    row = Brand(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        brand="Stripe",
        domain="stripe.com",
        website_url="",
        aliases=["斯特里普"],
        summary="",
    )
    with patch("aperix_geo.services.brand.cache.redis_set_json_persistent") as mock_set:
        remember_brand_row_domains(tenant_id=tenant_id, brand=row)
        assert mock_set.call_count == 2


@patch("aperix_geo.services.brand.domain.search_brand_official_domain")
@patch("aperix_geo.services.brand.domain.extract_domain_from_text_for_brand")
@patch("aperix_geo.services.brand.resolve.find_brand_by_name_or_alias")
@patch("aperix_geo.services.brand.domain.get_brand_domain_cached", return_value="stripe.com")
def test_resolve_brand_domain_uses_redis_before_db(
    mock_get_cache,
    mock_find_db,
    mock_extract,
    mock_search,
) -> None:
    domain = resolve_brand_domain(
        None,  # type: ignore[arg-type]
        tenant_id=uuid.uuid4(),
        brand="Stripe",
    )
    assert domain == "stripe.com"
    mock_get_cache.assert_called_once()
    mock_find_db.assert_not_called()
    mock_extract.assert_not_called()
    mock_search.assert_not_called()
