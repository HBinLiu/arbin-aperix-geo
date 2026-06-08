"""Tests for LLM response citation persistence."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock

from aperix_geo.db.models import CitationDomain, CitationUrl, Subject, SubjectType
from aperix_geo.services.sampling.citations import (
    aggregate_citation_urls,
    citations_from_parsed,
    domain_counts_from_url_rows,
    replace_citations_for_response,
)


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
                "url_type": "盘点清单文",
                "domain_type": "企业与品牌官网",
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
    assert by_url["https://blog.acme-brand.com/a"]["domain"] == "blog.acme-brand.com"
    assert by_url["https://blog.acme-brand.com/a"]["page_title"] == "Acme Blog Post"
    assert by_url["https://blog.acme-brand.com/a"]["url_type"] == "盘点清单文"
    assert by_url["https://blog.acme-brand.com/a"]["domain_type"] == "企业与品牌官网"
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
    assert domain_counts_from_url_rows(rows) == {
        "blog.acme-brand.com": 2,
        "docs.acme-brand.com": 1,
    }


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

    added = [call.args[0] for call in db.add.call_args_list]
    url_rows = [row for row in added if isinstance(row, CitationUrl)]
    domain_rows = [row for row in added if isinstance(row, CitationDomain)]
    assert len(url_rows) == 2
    assert len(domain_rows) == 1
    assert domain_rows[0].domain == "aperix.com"
    assert domain_rows[0].cite_count == 2
    assert url_rows[0].url == "https://aperix.com/page-a"
    assert url_rows[0].from_api is True


def test_aggregate_citation_urls_groups_metadata() -> None:
    subject = Subject(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        type=SubjectType.brand,
        brand="Aperix",
        website_url="https://aperix.com",
    )
    response_id = uuid.uuid4()
    rows = [
        MagicMock(id=response_id, parsed={"urls": ["https://stripe.com/blog/a"]}),
        MagicMock(id=uuid.uuid4(), parsed={"urls": ["https://stripe.com/blog/a"]}),
    ]
    records = [
        CitationUrl(
            response_id=response_id,
            prompt_id=uuid.uuid4(),
            url="https://stripe.com/blog/a",
            page_title="Stripe Blog",
            url_type="Article",
            llm_analysis={
                "analysis_source": "llm",
                "page_mentioned_brands": ["Beta"],
            },
        ),
        CitationUrl(
            response_id=rows[1].id,
            prompt_id=uuid.uuid4(),
            url="https://stripe.com/blog/a",
            page_title="Stripe Blog",
            url_type="Article",
            llm_analysis={
                "analysis_source": "llm",
                "page_mentioned_brands": ["Beta"],
            },
        ),
    ]
    db = MagicMock()
    db.execute.return_value.scalars.return_value.all.return_value = records

    aggregated = aggregate_citation_urls(db, rows, subject=subject)
    assert len(aggregated) == 1
    row = aggregated[0]
    assert row["url"] == "https://stripe.com/blog/a"
    assert row["title"] == "Stripe Blog"
    assert row["url_type"] == "Article"
    assert row["count"] == 2
    assert row["has_brand_analysis"] is True
    assert row["mentioned_brands"] == [{"label": "Beta", "domain": None}]
