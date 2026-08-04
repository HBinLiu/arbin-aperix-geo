"""Tests for homepage SEO rules and LLM domain_type fallback."""

from __future__ import annotations

from unittest.mock import patch

from aperix_geo.services.crawl.seo import SeoMetadata, SeoProfile, apply_seo_profile
from aperix_geo.services.domain.classify import classify_domain_type_with_llm
from aperix_geo.services.domain.type_rules import domain_type_from_homepage_seo
from aperix_geo.services.providers import LLMProviderError


def test_subject_homepage_profile_keeps_publisher() -> None:
    meta = SeoMetadata(title="T", publisher="新华社", schema_types=("NewsMediaOrganization",))
    scoped = apply_seo_profile(meta, SeoProfile.SUBJECT_HOMEPAGE)
    assert scoped.publisher == "新华社"
    assert "NewsMediaOrganization" in scoped.schema_types


def test_domain_type_from_schema_news() -> None:
    meta = SeoMetadata(schema_types=("Organization", "NewsMediaOrganization"))
    assert domain_type_from_homepage_seo("example.com", meta) == "news"


def test_domain_type_from_schema_hospital() -> None:
    meta = SeoMetadata(schema_types=("Hospital",))
    assert domain_type_from_homepage_seo("rmyy.example", meta) == "hospitals"


def test_domain_type_from_keywords_forum() -> None:
    meta = SeoMetadata(title="某某技术论坛", description="开发者讨论区")
    assert domain_type_from_homepage_seo("bbs.example", meta) == "forum"


def test_domain_type_from_keywords_jobsearch() -> None:
    meta = SeoMetadata(title="互联网招聘平台", keywords=("求职", "招聘"))
    assert domain_type_from_homepage_seo("jobs.example", meta) == "jobsearch"


def test_domain_type_uncertain_returns_empty() -> None:
    meta = SeoMetadata(title="Acme Widgets", description="We make widgets")
    assert domain_type_from_homepage_seo("acme.example", meta) == ""
    assert domain_type_from_homepage_seo("acme.example", None) == ""


def test_domain_type_from_schema_education() -> None:
    meta = SeoMetadata(schema_types=("CollegeOrUniversity",))
    assert domain_type_from_homepage_seo("univ.example", meta) == "education"


def test_domain_type_from_keywords_socialnet() -> None:
    meta = SeoMetadata(title="短视频社交平台", description="发现有趣内容")
    assert domain_type_from_homepage_seo("social.example", meta) == "socialnet"


def test_domain_type_from_keywords_science() -> None:
    meta = SeoMetadata(title="开发者文档", description="API 文档与开源社区")
    assert domain_type_from_homepage_seo("docs.example", meta) == "science"


def test_domain_type_prefers_longer_phrase() -> None:
    meta = SeoMetadata(title="互联网医院在线问诊平台")
    assert domain_type_from_homepage_seo("health.example", meta) == "hospitals"


def test_classify_domain_type_with_llm_accepts_closed_set() -> None:
    with patch(
        "aperix_geo.services.domain.classify.chat_completion",
        return_value=('{"domain_type":"finance"}', None, 10),
    ):
        assert classify_domain_type_with_llm(domain="bank.example", meta=None) == "finance"


def test_classify_domain_type_with_llm_rejects_unknown_code() -> None:
    with patch(
        "aperix_geo.services.domain.classify.chat_completion",
        return_value=('{"domain_type":"not-a-real-type"}', None, 10),
    ):
        assert classify_domain_type_with_llm(domain="x.example", meta=None) == ""


def test_classify_domain_type_with_llm_provider_error() -> None:
    with patch(
        "aperix_geo.services.domain.classify.chat_completion",
        side_effect=LLMProviderError("down"),
    ):
        assert classify_domain_type_with_llm(domain="x.example", meta=None) == ""
