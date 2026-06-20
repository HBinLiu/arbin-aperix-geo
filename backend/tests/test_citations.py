"""Tests for LLM response citation persistence."""

from __future__ import annotations

import threading
import uuid
from unittest.mock import MagicMock, patch
from aperix_geo.db.models import CitationDomain, CitationUrl, Prompt, Subject, SubjectType, Topic

from aperix_geo.services.sampling.citation import (
    CitationPageMeta,
    aggregate_citation_urls,
    citations_from_parsed,
    domain_counts_from_url_rows,
    fetch_citation_pages_parallel,
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


def test_aggregate_citation_urls_groups_metadata() -> None:
    subject = Subject(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        type=SubjectType.brand,
        brand="Aperix",
        website_url="https://aperix.com",
    )
    response_id = uuid.uuid4()
    prompt_id = uuid.uuid4()
    topic_id = uuid.uuid4()
    rows = [
        MagicMock(id=response_id, parsed={"urls": ["https://stripe.com/blog/a"]}, prompt_id=prompt_id),
        MagicMock(id=uuid.uuid4(), parsed={"urls": ["https://stripe.com/blog/a"]}, prompt_id=prompt_id),
    ]
    records = [
        CitationUrl(
            response_id=response_id,
            prompt_id=prompt_id,
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
            prompt_id=prompt_id,
            url="https://stripe.com/blog/a",
            page_title="Stripe Blog",
            url_type="Article",
            llm_analysis={
                "analysis_source": "llm",
                "page_mentioned_brands": ["Beta"],
            },
        ),
    ]
    prompt = Prompt(
        id=prompt_id,
        subject_id=subject.id,
        topic_id=topic_id,
        text="订购大模型品牌能见度监测系统",
        text_hash="abc",
    )
    topic = Topic(id=topic_id, subject_id=subject.id, name="AI品牌能见度监测")

    def _execute(stmt):
        entity = stmt.column_descriptions[0]["entity"]
        result = MagicMock()
        if entity is CitationUrl:
            result.scalars.return_value.all.return_value = records
        elif entity is Prompt:
            result.scalars.return_value.all.return_value = [prompt]
        elif entity is Topic:
            result.scalars.return_value.all.return_value = [topic]
        else:
            result.scalars.return_value.all.return_value = []
        return result

    db = MagicMock()
    db.execute.side_effect = _execute

    aggregated = aggregate_citation_urls(db, rows, subject=subject)
    assert len(aggregated) == 1
    row = aggregated[0]
    assert row["url"] == "https://stripe.com/blog/a"
    assert row["title"] == "Stripe Blog"
    assert row["url_type"] == "Article"
    assert row["count"] == 2
    assert row["has_brand_analysis"] is True
    assert row["mentioned_brands"] == [{"label": "Beta", "domain": None}]
    assert row["citing_prompts"] == [
        {"prompt_text": "订购大模型品牌能见度监测系统", "topic_name": "AI品牌能见度监测"},
    ]


def test_aggregate_citation_urls_skips_template_page_title() -> None:
    subject = Subject(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        type=SubjectType.brand,
        brand="Aperix",
        website_url="https://aperix.com",
    )
    response_id = uuid.uuid4()
    prompt_id = uuid.uuid4()
    rows = [
        MagicMock(
            id=response_id,
            parsed={"urls": ["https://example.com/article"]},
            prompt_id=prompt_id,
        ),
    ]
    records = [
        CitationUrl(
            response_id=response_id,
            prompt_id=prompt_id,
            url="https://example.com/article",
            page_title="{{content.leadTitle}}",
        ),
    ]

    def _execute(stmt):
        entity = stmt.column_descriptions[0]["entity"]
        result = MagicMock()
        if entity is CitationUrl:
            result.scalars.return_value.all.return_value = records
        else:
            result.scalars.return_value.all.return_value = []
        return result

    db = MagicMock()
    db.execute.side_effect = _execute

    aggregated = aggregate_citation_urls(db, rows, subject=subject)
    assert aggregated[0]["title"] == "https://example.com/article"


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
