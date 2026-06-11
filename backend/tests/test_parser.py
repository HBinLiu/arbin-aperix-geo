"""Tests for parse_llm_output extended fields."""

from __future__ import annotations

import time
import uuid
from contextlib import contextmanager
from unittest.mock import MagicMock, patch

from aperix_geo.db.models import Competitor, Subject, SubjectType
from aperix_geo.services.sampling.citation import CitationDocument, CitationPageMeta
from aperix_geo.services.sampling.mentions import competitor_entries, own_names
from aperix_geo.services.sampling.parse import parse_llm_output
from aperix_geo.services.sampling.parsed import ParsedSamplingResult
from aperix_geo.services.sampling.signal_draft import draft_to_record


import pytest


def _own_signal(parsed: ParsedSamplingResult) -> dict:
    for signal in parsed.entity_signals:
        if signal.entity_id == "own":
            return draft_to_record(signal)
    return {}


def _competitor_signals(parsed: ParsedSamplingResult) -> list[dict]:
    return [
        draft_to_record(signal)
        for signal in parsed.entity_signals
        if signal.entity_kind == "competitor"
    ]


def _default_page(url: str, *, text: str = "") -> CitationPageMeta:
    host = "aperix.com" if "aperix.com" in url else "example.com"
    return CitationPageMeta(
        url=url,
        domain=host,
        http_status=200,
        title="Test page",
        text_snippet=text,
        fetch_ok=bool(text),
    )


def _default_response_absa(*, own_brand: str, competitors: list[str], ai_mentioned: list[str]):
    brands = {
        own_brand: {
            "mentioned": own_brand in ai_mentioned,
            "score": 0.8 if own_brand in ai_mentioned else None,
            "evidence": "ai evidence" if own_brand in ai_mentioned else "",
        }
    }
    for name in competitors:
        brands[name] = {
            "mentioned": name in ai_mentioned,
            "score": 0.5 if name in ai_mentioned else None,
            "evidence": "",
        }
    return {
        "brands_sentiment_absa": brands,
        "other_brands_sentiment_absa": {},
        "analysis_source": "llm",
    }


def _default_page_geo(*, page_mentioned: list[str]):
    return {
        "domain_classification": {"type": "企业/品牌官网", "reason": "test"},
        "url_classification": {"type": "产品详情页", "reason": "test"},
        "page_mentioned_brands": page_mentioned,
        "analysis_source": "llm",
    }


@pytest.fixture(autouse=True)
def _patch_citation_fetch_by_default():
    def _fetch(url: str, **kwargs):
        return _default_page(url, text="")

    def _response_absa(raw_text, *, own_brand, competitors, **kwargs):
        ai_mentioned = []
        if own_brand and own_brand in raw_text:
            ai_mentioned.append(own_brand)
        for name in competitors:
            if name and name in raw_text:
                ai_mentioned.append(name)
        return _default_response_absa(
            own_brand=own_brand,
            competitors=competitors,
            ai_mentioned=ai_mentioned,
        )

    def _pages_geo(pages, *, own_brand, competitors, cache_ttl_s=0, batch_size=8):
        return [_default_page_geo(page_mentioned=[]) for _ in pages]

    mock_settings = MagicMock()
    mock_settings.deepseek_api_key = "sk-test"
    mock_settings.page_crawl_fetch_timeout_s = 10.0
    mock_settings.page_crawl_max_chars = 100000
    mock_settings.page_crawl_crawl_timeout_s = 45.0
    mock_settings.page_crawl_fallback_enabled = True
    mock_settings.page_crawl_concurrency = 10
    mock_settings.page_crawl_cache_ttl_s = 3600
    mock_settings.page_crawl_negative_cache_ttl_s = 300
    mock_settings.citation_text_snippet_chars = 5000
    mock_settings.citation_page_geo_llm_enabled = True
    mock_settings.citation_page_geo_cache_ttl_s = 3600
    mock_settings.citation_response_absa_cache_ttl_s = 3600
    mock_settings.citation_page_geo_batch_size = 8
    mock_settings.deepseek_chat_timeout_s = 120.0

    with (
        patch("aperix_geo.config.get_settings", return_value=mock_settings),
        patch("aperix_geo.services.sampling.citation.page.fetch_citation_page_meta", side_effect=_fetch),
        patch(
            "aperix_geo.services.sampling.parse.analysis.analyze_response_absa",
            side_effect=_response_absa,
        ),
        patch(
            "aperix_geo.services.sampling.citation.resolve.analyze_citation_pages_geo",
            side_effect=_pages_geo,
        ),
    ):
        yield


@contextmanager
def _mock_fetch_page(*, text: str = "Aperix product documentation and guides.", page_mentioned: list[str] | None = None):
    brands_on_page = page_mentioned if page_mentioned is not None else (
        ["Aperix"] if "Aperix" in text or "aperix" in text.lower() else []
    )

    def _fetch(url: str, **kwargs):
        return _default_page(url, text=text)

    def _response_absa(raw_text, *, own_brand, competitors, **kwargs):
        ai_mentioned = []
        if own_brand and own_brand in raw_text:
            ai_mentioned.append(own_brand)
        for name in competitors:
            if name and name in raw_text:
                ai_mentioned.append(name)
        return _default_response_absa(
            own_brand=own_brand,
            competitors=competitors,
            ai_mentioned=ai_mentioned,
        )

    def _pages_geo(pages, *, own_brand, competitors, cache_ttl_s=0, batch_size=8):
        return [_default_page_geo(page_mentioned=brands_on_page) for _ in pages]

    with (
        patch("aperix_geo.services.sampling.citation.page.fetch_citation_page_meta", side_effect=_fetch),
        patch(
            "aperix_geo.services.sampling.parse.analysis.analyze_response_absa",
            side_effect=_response_absa,
        ),
        patch(
            "aperix_geo.services.sampling.citation.resolve.analyze_citation_pages_geo",
            side_effect=_pages_geo,
        ),
    ):
        yield


def _brand_subject(**kwargs) -> Subject:
    subject = Subject(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        type=SubjectType.brand,
        brand=kwargs.get("brand", "Aperix"),
        aliases=kwargs.get("aliases", ["艾佩克斯"]),
        website_url=kwargs.get("website_url", "https://aperix.com"),
        domain=kwargs.get("domain", ""),
    )
    competitors = kwargs.get("competitors")
    if competitors is not None:
        subject.competitors = competitors
    return subject


def _competitor(*, brand: str = "", domain: str = "", subject_id: uuid.UUID | None = None) -> Competitor:
    return Competitor(
        id=uuid.uuid4(),
        subject_id=subject_id or uuid.uuid4(),
        brand=brand,
        domain=domain,
    )


def test_mention_count_and_rank():
    text = (
        "推荐 Aperix 和竞品 Beta。Aperix 产品优秀，Beta 也不错。"
        "详见 https://aperix.com/docs"
    )
    subject = _brand_subject(
        website_url="https://aperix.com",
        competitors=[_competitor(brand="Beta")],
    )
    with _mock_fetch_page(page_mentioned=["Aperix"]):
        parsed = parse_llm_output(text, subject=subject)
    own = _own_signal(parsed)
    assert own.get("mentioned") is True
    assert own.get("mention_count", 0) >= 2
    assert any(signal.get("mention_count", 0) >= 1 for signal in _competitor_signals(parsed))
    assert own.get("mention_rank") == 1
    assert own.get("has_domain_link") is True
    assert own.get("cited_on_source") is True
    assert parsed.citation_urls_own
    assert parsed.citation_response_absa["brands_sentiment_absa"]["Aperix"]["mentioned"] is True
    assert own.get("sentiment_label") == "positive"
    assert own.get("sentiment_score") == 90.0


def test_citation_requires_source_page_brand_mention():
    text = "推荐阅读 https://aperix.com/docs 这篇文章。"
    subject = _brand_subject(website_url="https://aperix.com")
    with _mock_fetch_page(text="Generic article about cloud computing.", page_mentioned=[]):
        parsed = parse_llm_output(text, subject=subject)
    own = _own_signal(parsed)
    assert own.get("has_domain_link") is True
    assert own.get("cited_on_source") is False


def test_no_own_mention():
    text = "今天天气不错，没有提到任何品牌。"
    subject = _brand_subject(competitors=[_competitor(brand="Beta")])
    parsed = parse_llm_output(text, subject=subject)
    own = _own_signal(parsed)
    assert own.get("mentioned") is False
    assert own.get("mention_count") == 0
    assert own.get("mention_rank") is None
    assert own.get("sentiment_score") is None


def test_competitor_ranked_first():
    text = "Beta 领先，Aperix 紧随其后。"
    subject = _brand_subject(competitors=[_competitor(brand="Beta")])
    parsed = parse_llm_output(text, subject=subject)
    own = _own_signal(parsed)
    assert own.get("mentioned") is True
    assert own.get("mention_rank") == 2


def test_own_names_includes_brand_and_domain():
    subject = _brand_subject(brand="Aperix", domain="aperix.com", aliases=["APX"])
    names = own_names(subject)
    assert "Aperix" in names
    assert "aperix.com" in names
    assert "APX" in names


def test_domain_subject_mention_by_domain_string():
    subject = Subject(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        type=SubjectType.domain,
        brand="",
        domain="aperix.com",
        website_url="https://aperix.com",
    )
    text = "推荐 aperix.com 上的产品。"
    parsed = parse_llm_output(text, subject=subject)
    assert _own_signal(parsed).get("mentioned") is True


def test_competitor_entries_merge_brand_and_domain():
    subject = _brand_subject(
        competitors=[
            _competitor(brand="Beta", domain="beta.com"),
            _competitor(brand="", domain="gamma.io"),
        ]
    )
    entries = competitor_entries(subject)
    assert len(entries) == 2
    labels = {e.label for e in entries}
    assert "beta.com" in labels or "Beta" in labels


def test_competitor_mention_by_brand_with_domain_on_record():
    text = "Beta 是不错的选择。"
    subject = _brand_subject(competitors=[_competitor(brand="Beta", domain="beta.com")])
    parsed = parse_llm_output(text, subject=subject)
    assert any(signal.get("mentioned") for signal in _competitor_signals(parsed))


def test_competitor_mention_via_url_host_only():
    text = "详见 https://beta.com/product"
    subject = _brand_subject(competitors=[_competitor(brand="Beta", domain="beta.com")])
    parsed = parse_llm_output(text, subject=subject)
    assert any(signal.get("mentioned") for signal in _competitor_signals(parsed))


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
        return {"brands_sentiment_absa": {}, "analysis_source": "llm"}

    def _slow_citation(**kwargs):
        marks["citation_start"] = time.monotonic()
        time.sleep(0.25)
        marks["citation_end"] = time.monotonic()
        return CitationDocument()

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
            "aperix_geo.services.sampling.parse.analysis.analyze_response_absa",
            side_effect=_slow_absa,
        ),
        patch(
            "aperix_geo.services.sampling.parse.analysis.resolve_citation_sources",
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
