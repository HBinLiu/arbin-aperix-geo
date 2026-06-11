"""Tenant-scoped brand registry."""

from aperix_geo.services.brand.cache import (
    clear_brand_domain_cache,
    get_brand_domain_cached,
    remember_brand_domain_cached,
)
from aperix_geo.services.brand.catalog import BrandCatalog, BrandSyncContext
from aperix_geo.services.brand.domain import (
    extract_domain_from_text_for_brand,
    other_entity_id,
    resolve_brand_domain,
    search_brand_official_domain,
)
from aperix_geo.services.brand.keys import configured_brand_keys
from aperix_geo.services.brand.resolve import (
    find_brand_by_domain,
    find_brand_by_name,
    find_brand_by_name_or_alias,
    normalize_brand_key,
    primary_domain_for_brand,
    resolve_or_create_brand,
)
from aperix_geo.services.brand.sync import sync_brand_for_entity, sync_brands_for_entities
from aperix_geo.services.brand.types import BrandSyncEntity

__all__ = [
    "BrandCatalog",
    "BrandSyncContext",
    "BrandSyncEntity",
    "clear_brand_domain_cache",
    "configured_brand_keys",
    "extract_domain_from_text_for_brand",
    "find_brand_by_domain",
    "find_brand_by_name",
    "find_brand_by_name_or_alias",
    "get_brand_domain_cached",
    "normalize_brand_key",
    "other_entity_id",
    "primary_domain_for_brand",
    "remember_brand_domain_cached",
    "resolve_brand_domain",
    "resolve_or_create_brand",
    "search_brand_official_domain",
    "sync_brand_for_entity",
    "sync_brands_for_entities",
]
