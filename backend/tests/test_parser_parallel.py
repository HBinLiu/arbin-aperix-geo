"""Tests that ABSA and citation resolution run concurrently."""

from __future__ import annotations

import time
import uuid
from unittest.mock import MagicMock, patch

from aperix_geo.db.models import Subject, SubjectType
from aperix_geo.services.sampling.parser import parse_llm_output


def test_parse_llm_output_runs_absa_and_citation_in_parallel() -> None:
    subject = Subject(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        type=SubjectType.brand,
        brand="Aperix",
        aliases=[],
        website_url="https://aperix.com",
        domain="aperix.com",
    )
    subject.competitors = []

    marks: dict[str, float] = {}

    def _slow_absa(raw_text, **kwargs):
        marks["absa_start"] = time.monotonic()
        time.sleep(0.25)
        marks["absa_end"] = time.monotonic()
        return {"analysis_timestamp": "t", "brands_sentiment_absa": {}, "analysis_source": "llm"}

    def _slow_citation(**kwargs):
        marks["citation_start"] = time.monotonic()
        time.sleep(0.25)
        marks["citation_end"] = time.monotonic()
        return {
            "citation_urls_own": [],
            "has_own_domain_link": False,
            "cited_own_domain": False,
            "citation_sources": [],
            "has_competitor_domain_links": {},
            "cited_competitors_on_source": {},
        }

    mock_settings = MagicMock()
    mock_settings.deepseek_api_key = "sk-test"
    mock_settings.page_crawl_fetch_timeout_s = 8.0
    mock_settings.page_crawl_crawl_timeout_s = 45.0
    mock_settings.page_crawl_max_chars = 120000
    mock_settings.page_crawl_fallback_enabled = True
    mock_settings.page_crawl_concurrency = 10
    mock_settings.page_crawl_cache_ttl_s = 3600
    mock_settings.page_crawl_negative_cache_ttl_s = 300
    mock_settings.page_crawl_dns_cache_ttl_s = 3600
    mock_settings.citation_text_snippet_chars = 4000
    mock_settings.citation_page_geo_llm_enabled = True
    mock_settings.citation_page_geo_cache_ttl_s = 3600
    mock_settings.citation_response_absa_cache_ttl_s = 3600
    mock_settings.citation_page_geo_batch_size = 8
    mock_settings.deepseek_chat_timeout_s = 120.0

    started = time.monotonic()
    with (
        patch("aperix_geo.config.get_settings", return_value=mock_settings),
        patch(
            "aperix_geo.services.sampling.citation_analysis.analyze_citation_response_absa",
            side_effect=_slow_absa,
        ),
        patch(
            "aperix_geo.services.sampling.parser._resolve_citation_sources",
            side_effect=_slow_citation,
        ),
    ):
        parse_llm_output(
            "Aperix is great https://aperix.com/docs",
            subject=subject,
            source_urls=["https://aperix.com/docs"],
        )

    elapsed = time.monotonic() - started
    assert marks["absa_start"] < marks["citation_end"]
    assert marks["citation_start"] < marks["absa_end"]
    assert elapsed < 0.45
