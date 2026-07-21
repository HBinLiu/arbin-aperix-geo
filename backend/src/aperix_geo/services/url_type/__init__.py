"""URL / page-type classification via official rs-trafilatura."""

from aperix_geo.services.url_type.classify import classify_page_type, classify_url, classify_url_type
from aperix_geo.services.url_type.extract import extract_main_content
from aperix_geo.services.url_type.taxonomy import DEFAULT_URL_TYPE, URL_TYPES, normalize_url_type

__all__ = [
    "DEFAULT_URL_TYPE",
    "URL_TYPES",
    "classify_page_type",
    "classify_url",
    "classify_url_type",
    "extract_main_content",
    "normalize_url_type",
]
