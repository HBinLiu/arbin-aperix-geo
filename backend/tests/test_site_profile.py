"""Tests for micro-niche profile normalization and search query."""

from aperix_geo.services.competitor.profile import (
    _split_tags,
    build_search_query,
    merge_profile_updates,
    normalize_niche_profile,
    profile_from_dict,
    search_queries_list,
)
from aperix_geo.services.competitor.summary import (
    fallback_profile_summary,
    merge_competitors_into_summary,
    replace_summary_section,
)
from aperix_geo.services.setup.helpers import company_from_session


def test_normalize_profile_micro_niche() -> None:
    profile = normalize_niche_profile(
        {
            "industry": "医疗影像AI诊断与辅助决策系统",
            "features": ["AI辅助结节检测", "云端PACS工作流集成", "多余"],
            "customers": "三甲医院放射科、医学影像中心",
            "keywords": ["医疗影像AI诊断", "肺结节AI筛查", "云PACS影像系统", "DICOM智能阅片"],
        },
        entity="deepwise.com",
    )
    assert profile["industry"] == "医疗影像AI诊断与辅助决策系统"
    assert "AI辅助结节检测" in profile["features"]
    assert profile["features"].count("、") <= 2
    assert "肺结节AI筛查" in profile["search_queries"]


def test_search_queries_list() -> None:
    profile = normalize_niche_profile(
        {
            "industry": "跨境支付",
            "features": ["收款"],
            "customers": "企业",
            "keywords": ["跨境B2B", "多币种", "企业全球", "国际汇款"],
        },
        entity="example.com",
    )
    assert search_queries_list(profile) == ["跨境B2B", "多币种", "企业全球", "国际汇款"]


def test_merge_profile_updates_keywords() -> None:
    base = profile_from_dict(
        {
            "company": "Acme",
            "industry": "SaaS",
            "features": "支付",
            "customers": "企业",
            "keywords": "旧词一、旧词二",
        },
    )
    merged = merge_profile_updates(base, search_queries=["跨境支付", "多币种账户", "企业钱包", "国际汇款"])
    assert "跨境支付" in merged["search_queries"]
    assert "旧词一" not in merged["search_queries"]


def test_keywords_accepts_five() -> None:
    base = profile_from_dict(
        {
            "company": "Acme",
            "industry": "SaaS",
            "features": "支付",
            "customers": "企业",
            "keywords": "旧词",
        },
    )
    keywords = ["主题一", "主题二", "主题三", "主题四", "主题五"]
    merged = merge_profile_updates(base, search_queries=keywords)
    assert _split_tags(merged["search_queries"]) == keywords


def test_keywords_not_truncated() -> None:
    profile = normalize_niche_profile(
        {
            "industry": "跨境支付",
            "features": ["收款"],
            "customers": "企业",
            "keywords": [
                "跨境B2B收款平台",
                "多币种",
                "企业全球账户系统",
                "国际汇款",
            ],
        },
        entity="example.com",
    )
    parts = _split_tags(profile["search_queries"])
    assert parts == [
        "跨境B2B收款平台",
        "多币种",
        "企业全球账户系统",
        "国际汇款",
    ]


def test_search_query_prefers_keywords() -> None:
    profile = normalize_niche_profile(
        {
            "industry": "医疗影像AI诊断与辅助决策系统",
            "features": ["AI辅助结节检测"],
            "customers": "三甲医院放射科",
            "keywords": ["医疗影像AI诊断", "肺结节AI筛查", "云PACS影像系统", "DICOM智能阅片"],
        },
        entity="deepwise.com",
    )
    q = build_search_query(profile)
    assert q is not None
    assert "医疗影像AI诊断" in q
    assert "肺结节AI筛查" in q


def test_fallback_profile_summary_sections() -> None:
    profile = profile_from_dict(
        {
            "company": "示例品牌",
            "industry": "跨境 B2B 支付",
            "features": "多币种收款、合规结汇",
            "customers": "出海中小企业",
            "search_queries": "跨境收款、多币种账户",
        },
    )
    summary = fallback_profile_summary(profile, entity="示例品牌", region_label="中国大陆")
    assert summary.startswith("# 示例品牌")
    assert "## 概述" in summary
    assert "## 竞品" in summary
    assert "## 理想客户画像" in summary
    assert "## 地域与合规" in summary
    assert "待补充" in summary
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
