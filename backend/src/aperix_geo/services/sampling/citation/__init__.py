"""Citation source fetch, resolution, and DB persistence."""

from aperix_geo.services.sampling.citation.cache import clear_job_citation_page_cache
from aperix_geo.services.sampling.citation.labels import (
    brand_names_match,
    page_mentioned_brand_names,
)
from aperix_geo.services.sampling.citation.page import (
    CitationPageMeta,
    fetch_citation_page_meta,
    fetch_citation_pages_parallel,
    page_mentioned_brands_from_snippet,
)
from aperix_geo.services.sampling.citation.persist import (
    citations_from_parsed,
    domain_counts_from_url_rows,
    replace_citations_for_response,
)
from aperix_geo.services.sampling.citation.document import CitationDocument, empty_citation_document
from aperix_geo.services.sampling.citation.resolve import citation_root

__all__ = [
    "CitationPageMeta",
    "CitationDocument",
    "brand_names_match",
    "citation_root",
    "citations_from_parsed",
    "clear_job_citation_page_cache",
    "domain_counts_from_url_rows",
    "empty_citation_document",
    "fetch_citation_page_meta",
    "fetch_citation_pages_parallel",
    "page_mentioned_brand_names",
    "page_mentioned_brands_from_snippet",
    "replace_citations_for_response",
]
