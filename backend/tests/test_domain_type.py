"""Tests for domain type taxonomy and seed classification."""

from __future__ import annotations

from aperix_geo.services.domain.seeds import seed_domain_type
from aperix_geo.services.domain.taxonomy import DOMAIN_TYPES, normalize_domain_type


def test_normalize_domain_type_accepts_shallalist_codes() -> None:
    assert normalize_domain_type("News") == "news"
    assert normalize_domain_type("unknown-xyz") == "other"
    assert normalize_domain_type("") == "other"
    assert normalize_domain_type(None) == "other"
    assert "socialnet" in DOMAIN_TYPES
    assert "other" in DOMAIN_TYPES


def test_seed_domain_type_common_hosts() -> None:
    assert seed_domain_type("zhihu.com") == "socialnet"
    assert seed_domain_type("wikipedia.org") == "education"
    assert seed_domain_type("jd.com") == "shopping"
    assert seed_domain_type("example-unknown-brand.test") == ""
