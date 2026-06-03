"""Tests for parse_llm_output extended fields."""

from __future__ import annotations

import uuid

from aperix_geo.db.models import Subject, SubjectType
from aperix_geo.services.sampling.parser import parse_llm_output


def _brand_subject(**kwargs) -> Subject:
    return Subject(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        type=SubjectType.brand,
        brand=kwargs.get("brand", "Aperix"),
        aliases=kwargs.get("aliases", ["艾佩克斯"]),
        website_url=kwargs.get("website_url", "https://aperix.com"),
        domain=kwargs.get("domain", ""),
    )


def test_mention_count_and_rank():
    text = (
        "推荐 Aperix 和竞品 Beta。Aperix 产品优秀，Beta 也不错。"
        "详见 https://aperix.com/docs"
    )
    subject = _brand_subject(website_url="https://aperix.com")
    parsed = parse_llm_output(
        text,
        subject=subject,
        competitor_domains=[],
        competitor_brands=["Beta"],
    )
    assert parsed["mentions_own"] is True
    assert parsed["mention_count_own"] >= 2
    assert parsed["mention_counts_competitors"]["Beta"] >= 1
    assert parsed["rank_own"] == 1
    assert parsed["cited_own_domain"] is True
    assert parsed["citation_urls_own"]
    assert parsed["sentiment_own"] == "positive"
    assert parsed["sentiment_score_own"] == 1.0


def test_no_own_mention():
    text = "今天天气不错，没有提到任何品牌。"
    subject = _brand_subject()
    parsed = parse_llm_output(
        text,
        subject=subject,
        competitor_domains=[],
        competitor_brands=["Beta"],
    )
    assert parsed["mentions_own"] is False
    assert parsed["mention_count_own"] == 0
    assert parsed["rank_own"] is None
    assert parsed["sentiment_score_own"] is None


def test_competitor_ranked_first():
    text = "Beta 领先，Aperix 紧随其后。"
    subject = _brand_subject()
    parsed = parse_llm_output(
        text,
        subject=subject,
        competitor_domains=[],
        competitor_brands=["Beta"],
    )
    assert parsed["mentions_own"] is True
    assert parsed["rank_own"] == 2
