"""Unified network identity helpers — single import surface for URL / host / domain logic.

Semantic layers (pick the narrowest that fits):

- ``host_from`` — normalized hostname (subdomains preserved)
- ``registrable_from`` — eTLD+1 string (DB keys, dedupe, citation aggregation)
- ``registrable_root_has_dns`` — whether eTLD+1 (or www) resolves in DNS
- ``brand_from`` — validated brand primary domain (eTLD+1)
- ``favicon_from`` — favicon cache key (meaningful subdomains kept)
- ``citation_registrable_key`` — normalize user URL/host input to citation DB key
- ``validate_optional_http_url`` (schemas) — **storage**: preserve user scheme; bare host ok
- ``parse_url`` — **fetch**: always http(s), bare input defaults to ``http://``
- ``website_candidates`` / ``resolve_website`` — probe homepage with https then http
- ``crawl_cache_url`` — crawl cache key normalization
- ``host_under_root`` — whether a host belongs to a registrable root

Business modules should import from this module only (enforced by ``tests/test_import_conventions.py``).
"""

from __future__ import annotations

from aperix_geo.utils.domains import (
    brand_from,
    dedupe_domains,
    ensure_brand,
    favicon_from,
    host_from,
    is_brand_domain,
    is_valid_hostname,
    registrable_from,
    site_name_from_title,
    title_alias_candidates,
)
from aperix_geo.utils.dns import (
    clear_dns_cache,
    dns_cache_ttl_s,
    dns_timeout_s,
    host_has_dns_records,
    registrable_root_has_dns,
)
from aperix_geo.utils.url import (
    apex_homepage_urls,
    append_http_homepage_variants,
    citation_registrable_key,
    crawl_cache_url,
    extract_urls,
    filter_citation_urls,
    homepage_url_candidates,
    homepage_urls,
    host_resolves,
    host_resolves_public,
    host_under_root,
    is_citation_host,
    is_llm_numeric_fake_url,
    is_placeholder_citation_host,
    parse_url,
    profile_crawl_urls,
    resolve_website,
    website_candidates,
)

__all__ = [
    "clear_dns_cache",
    "dns_cache_ttl_s",
    "dns_timeout_s",
    "apex_homepage_urls",
    "append_http_homepage_variants",
    "brand_from",
    "citation_registrable_key",
    "crawl_cache_url",
    "dedupe_domains",
    "ensure_brand",
    "extract_urls",
    "favicon_from",
    "filter_citation_urls",
    "homepage_url_candidates",
    "homepage_urls",
    "host_from",
    "host_has_dns_records",
    "host_resolves",
    "host_resolves_public",
    "host_under_root",
    "is_brand_domain",
    "is_citation_host",
    "is_llm_numeric_fake_url",
    "is_placeholder_citation_host",
    "is_valid_hostname",
    "parse_url",
    "profile_crawl_urls",
    "registrable_from",
    "registrable_root_has_dns",
    "resolve_website",
    "site_name_from_title",
    "title_alias_candidates",
    "website_candidates",
]
