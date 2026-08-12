"""Tests for slim niche profile normalization."""

from aperix_geo.services.competitor.profile import (
    keywords_list,
    merge_profile_updates,
    normalize_niche_profile,
    profile_from_dict,
)
from aperix_geo.services.competitor.summary import (
    fallback_profile_summary,
    merge_competitors_into_summary,
    replace_summary_section,
)
from aperix_geo.services.setup.helpers import company_from_session


def test_normalize_profile_slim() -> None:
    profile = normalize_niche_profile(
        {
            "industry": "医疗影像AI诊断与辅助决策系统",
            "keywords": ["AI辅助结节检测", "云端PACS", "DICOM阅片"],
            "brief": "三甲医院放射科",
        },
        entity="deepwise.com",
    )
    assert profile["industry"] == "医疗影像AI诊断与辅助决策系统"
    assert keywords_list(profile) == ["AI辅助结节检测", "云端PACS", "DICOM阅片"]
    assert "三甲医院" in profile["brief"]


def test_normalize_ignores_legacy_fields() -> None:
    profile = normalize_niche_profile(
        {
            "industry": "跨境支付",
            "features": ["收款", "换汇"],
            "customers": "出海中小企业",
            "topic_lexicon": {"category_terms": ["跨境收款", "多币种账户"]},
        },
        entity="example.com",
    )
    assert keywords_list(profile) == []
    assert profile["brief"] == ""


def test_merge_profile_updates_keywords() -> None:
    base = profile_from_dict(
        {
            "company": "Acme",
            "industry": "SaaS",
            "keywords": "旧词一、旧词二",
            "brief": "企业",
        },
    )
    merged = merge_profile_updates(base, profile_patch={"keywords": "跨境支付、多币种账户"})
    assert keywords_list(merged) == ["跨境支付", "多币种账户"]


def test_fallback_profile_summary_sections() -> None:
    profile = profile_from_dict(
        {
            "company": "示例品牌",
            "industry": "跨境 B2B 支付",
            "keywords": "多币种收款、合规结汇",
            "brief": "出海中小企业",
        },
    )
    summary = fallback_profile_summary(profile, entity="示例品牌", region_label="中国大陆")
    assert summary.startswith("# 示例品牌")
    assert "## 概述" in summary
    assert "## 竞品" in summary
    assert "多币种收款" in summary
    assert "中国大陆" in summary


def test_merge_competitors_into_summary_domain() -> None:
    base = (
        "# 示例\n\n## 概述\n测试\n\n## 竞品\n* **待补充：** 将在竞品搜索阶段完善\n\n"
        "## 核心价值\n价值\n"
    )
    updated = merge_competitors_into_summary(
        base,
        subject_type="domain",
        competitors=[
            {"domain": "rival.com", "brand": "竞品A", "summary": "同业竞品"},
            {"domain": "other.cn", "brand": "竞品B", "summary": "同业竞品"},
        ],
    )
    assert "rival.com" in updated
    assert "竞品A" in updated
    assert "待补充" not in updated
    assert "## 核心价值" in updated


def test_merge_competitors_into_summary_brand() -> None:
    base = "# 品牌\n\n## 竞品\n* **待补充：** 将在竞品搜索阶段完善\n"
    updated = merge_competitors_into_summary(
        base,
        subject_type="brand",
        competitors=[
            {"domain": "", "brand": "竞品甲", "summary": "简介甲"},
            {"domain": "", "brand": "竞品乙", "summary": "简介乙"},
        ],
    )
    assert "竞品甲" in updated
    assert "简介甲" in updated


def test_replace_summary_section() -> None:
    base = (
        "# 示例\n\n## 市场定位\n旧定位\n\n## 理想客户画像\n旧 ICP\n\n## 决策触发点\n旧问题\n"
    )
    updated = replace_summary_section(base, "市场定位", "面向细分赛道的专业供应商。")
    updated = replace_summary_section(
        updated,
        "理想客户画像",
        "医疗 | 100-500 人 | 信息科主任。典型场景：升级 PACS。",
    )
    assert "面向细分赛道" in updated
    assert "信息科主任" in updated
    assert "旧定位" not in updated


def test_company_from_session() -> None:
    assert company_from_session({"profile": {"company": "深睿医疗"}}) == "深睿医疗"
    assert company_from_session(None) is None
