"""Domain profile / classification package."""

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


def __getattr__(name: str):
    if name in {
        "classify_domains",
        "domain_types_for",
        "ensure_domain_profiles",
        "maybe_enqueue_domain_type_classify",
    }:
        from aperix_geo.services.domain import classify as _classify

        return getattr(_classify, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
