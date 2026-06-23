"""Tests for LLM response citation persistence."""

from __future__ import annotations

import threading
from unittest.mock import MagicMock, patch
from aperix_geo.db.models import CitationDomain, CitationUrl

from aperix_geo.services.sampling.citation import (
    CitationPageMeta,
    citations_from_parsed,
    domain_counts_from_url_rows,
    fetch_citation_pages_parallel,
    replace_citations_for_response,
)
from aperix_geo.services.sampling.citation.page import sort_citation_urls_for_fetch


def test_citations_from_parsed_dedupes_and_maps_source_metadata() -> None:
    parsed = {
        "urls": [
            "https://blog.acme-brand.com/a",
            "https://blog.acme-brand.com/a",
            "https://docs.acme-brand.com/b",
        ],
        "source_urls_from_api": ["https://docs.acme-brand.com/b"],
        "citation_sources": [
            {
                "url": "https://blog.acme-brand.com/a",
                "fetch_ok": True,
                "page_title": "Acme Blog Post",
                "http_status": 200,
                "description": "desc",
                "headings": ["H1"],
                "has_table": False,
                "has_code_block": False,
                "text_snippet": "body",
                "llm_analysis": {
                    "analysis_source": "llm",
                    "page_mentioned_brands": ["Acme"],
                },
            }
        ],
    }
    rows = citations_from_parsed(parsed)
    assert len(rows) == 2
    by_url = {row["url"]: row for row in rows}
    assert by_url["https://blog.acme-brand.com/a"]["domain"] == "acme-brand.com"
    assert by_url["https://blog.acme-brand.com/a"]["page_title"] == "Acme Blog Post"
    assert by_url["https://docs.acme-brand.com/b"]["from_api"] is True


def test_citations_from_parsed_skips_placeholder_domains() -> None:
    parsed = {
        "urls": [
            "https://example.com/page",
            "https://www.example.org/foo",
            "https://aperix.com/real",
        ],
        "source_urls_from_api": [],
        "citation_sources": [],
    }
    rows = citations_from_parsed(parsed)
    assert len(rows) == 1
    assert rows[0]["url"] == "https://aperix.com/real"


def test_domain_counts_from_url_rows() -> None:
    rows = citations_from_parsed(
        {
            "urls": [
                "https://blog.acme-brand.com/a",
                "https://blog.acme-brand.com/b",
                "https://docs.acme-brand.com/c",
            ],
            "citation_sources": [],
            "source_urls_from_api": [],
        }
    )
    assert domain_counts_from_url_rows(rows) == {"acme-brand.com": 3}


def test_replace_citations_for_response_inserts_url_and_domain_rows() -> None:
    db = MagicMock()
    parsed = {
        "urls": [
            "https://aperix.com/page-a",
            "https://aperix.com/page-b",
        ],
        "source_urls_from_api": ["https://aperix.com/page-a"],
        "citation_sources": [],
    }
    count = replace_citations_for_response(
        db,
        response_id="00000000-0000-0000-0000-000000000001",
        prompt_id="00000000-0000-0000-0000-000000000002",
        parsed=parsed,
    )
    assert count == 2
    assert db.execute.call_count == 2
    db.flush.assert_called_once()

    added = [call.args[0] for call in db.add.call_args_list]
    url_rows = [row for row in added if isinstance(row, CitationUrl)]
    domain_rows = [row for row in added if isinstance(row, CitationDomain)]
    assert len(url_rows) == 2
    assert len(domain_rows) == 1
    assert domain_rows[0].domain == "aperix.com"
    assert domain_rows[0].cite_count == 2
    assert url_rows[0].url == "https://aperix.com/page-a"
    assert url_rows[0].from_api is True


def test_fetch_citation_pages_parallel_preserves_order() -> None:
    urls = ["https://a.test/1", "https://b.test/2", "https://c.test/3"]
    active = {"n": 0}
    lock = threading.Lock()

    def _fetch(url: str, **kwargs) -> CitationPageMeta:
        with lock:
            active["n"] += 1
            assert active["n"] <= 2
        try:
            host = url.split("/")[2]
            return CitationPageMeta(url=url, domain=host, fetch_ok=True, title=host)
        finally:
            with lock:
                active["n"] -= 1

    with patch(
        "aperix_geo.services.sampling.citation.page.fetch_citation_page_meta",
        side_effect=_fetch,
    ):
        pages = fetch_citation_pages_parallel(urls, concurrency=2)

    assert [p.url for p in pages] == urls
    assert [p.title for p in pages] == ["a.test", "b.test", "c.test"]


def test_sort_citation_urls_for_fetch_prioritizes_own_and_competitors() -> None:
    urls = [
        "https://other.com/x",
        "https://aperix.com/a",
        "https://rival.com/b",
        "https://aperix.com/b",
    ]
    ordered = sort_citation_urls_for_fetch(
        urls,
        own_root="aperix.com",
        competitor_roots={"rival.com"},
    )
    assert ordered == [
        "https://aperix.com/a",
        "https://aperix.com/b",
        "https://rival.com/b",
        "https://other.com/x",
    ]
