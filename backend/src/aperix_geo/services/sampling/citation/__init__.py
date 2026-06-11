"""Citation source fetch, LLM analysis, resolution, and DB persistence."""

from aperix_geo.services.sampling.citation.aggregate import (
    aggregate_citation_domains,
    aggregate_citation_urls,
)
from aperix_geo.services.sampling.citation.cache import (
    clear_job_citation_page_cache,
    clear_page_geo_cache,
)
from aperix_geo.services.sampling.citation.labels import (
    ai_mentioned_brand_names,
    brand_names_match,
    page_mentioned_brand_names,
)
from aperix_geo.services.sampling.citation.page import (
    CitationPageMeta,
    fetch_citation_page_meta,
    fetch_citation_pages_parallel,
    page_mentions_any_term,
)
from aperix_geo.services.sampling.citation.page_geo import (
    analyze_citation_page_geo,
    analyze_citation_pages_geo,
    heuristic_page_mentioned_brands,
    normalize_page_geo,
)
from aperix_geo.services.sampling.citation.persist import (
    citations_from_parsed,
    domain_counts_from_url_rows,
    replace_citations_for_response,
)
from aperix_geo.services.sampling.citation.document import CitationDocument, empty_citation_document
from aperix_geo.services.sampling.citation.resolve import (
    citation_root,
    resolve_citation_sources,
)

__all__ = [
    "CitationPageMeta",
    "CitationDocument",
    "aggregate_citation_domains",
    "aggregate_citation_urls",
    "ai_mentioned_brand_names",
    "analyze_citation_page_geo",
    "analyze_citation_pages_geo",
    "brand_names_match",
    "citation_root",
    "citations_from_parsed",
    "clear_job_citation_page_cache",
    "clear_page_geo_cache",
    "domain_counts_from_url_rows",
    "empty_citation_document",
    "fetch_citation_page_meta",
    "fetch_citation_pages_parallel",
    "heuristic_page_mentioned_brands",
    "normalize_page_geo",
    "page_mentioned_brand_names",
    "page_mentions_any_term",
    "replace_citations_for_response",
    "resolve_citation_sources",
]
