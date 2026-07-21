"""Domain profile / classification package."""

from aperix_geo.services.domain.classify import (
    classify_domains,
    domain_types_for,
    ensure_domain_profiles,
    maybe_enqueue_domain_type_classify,
)
from aperix_geo.services.domain.taxonomy import DOMAIN_TYPES, DEFAULT_DOMAIN_TYPE, normalize_domain_type

__all__ = [
    "DEFAULT_DOMAIN_TYPE",
    "DOMAIN_TYPES",
    "classify_domains",
    "domain_types_for",
    "ensure_domain_profiles",
    "maybe_enqueue_domain_type_classify",
    "normalize_domain_type",
]
