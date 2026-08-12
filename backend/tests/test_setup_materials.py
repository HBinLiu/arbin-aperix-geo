"""Tests for brand setup materials validation."""

from __future__ import annotations

import pytest

from aperix_geo.services.competitor.profile import normalize_niche_profile
from aperix_geo.services.setup.exceptions import MaterialsInsufficientError
from aperix_geo.services.setup.llm.payloads import build_subject_research_payload
from aperix_geo.services.setup.materials import (
    assert_brand_corpus_sufficient,
    assert_niche_profile_sufficient,
    build_user_corpus,
    effective_corpus_chars,
    is_niche_profile_sufficient,
)


def test_build_brand_research_payload_uses_user_corpus_only() -> None:
    payload = build_subject_research_payload(
        subject_type="brand",
        target="深睿医疗",
        region="CN",
        language="zh-CN",
        user_corpus="品牌介绍正文" * 50,
        homepage_text="首页正文",
        website_url="https://example.com",
    )
    assert payload["mode"] == "brand"
    assert "web_research" not in payload
    assert payload["user_corpus"]
    assert payload["homepage"]["url"] == "https://example.com"


def test_assert_brand_corpus_insufficient_raises() -> None:
    with pytest.raises(MaterialsInsufficientError) as exc:
        assert_brand_corpus_sufficient(user_corpus="太短", homepage_text="")
    assert exc.value.code == "materials_insufficient"


def test_effective_corpus_chars_ignores_whitespace() -> None:
    intro = "a" * 200 + " " * 50 + "b" * 100
    assert effective_corpus_chars(user_corpus=intro) == 300


def test_is_niche_profile_sufficient() -> None:
    ok = normalize_niche_profile(
        {
            "industry": "医疗 AI",
            "keywords": ["影像诊断", "AI 医学影像"],
            "brief": "三甲医院",
        },
        entity="深睿医疗",
    )
    assert is_niche_profile_sufficient(ok) is True

    weak = normalize_niche_profile({"industry": "未知行业"}, entity="某品牌")
    assert is_niche_profile_sufficient(weak) is False

    with pytest.raises(MaterialsInsufficientError):
        assert_niche_profile_sufficient(weak)


def test_build_user_corpus_merges_intro_and_uploads() -> None:
    corpus = build_user_corpus(
        brand_intro="介绍",
        upload_files=[{"extracted_text": "文件内容"}],
    )
    assert "介绍" in corpus
    assert "文件内容" in corpus
