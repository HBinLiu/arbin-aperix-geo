"""Tests for micro-niche profile normalization and search query."""

from aperix_geo.services.competitor.profile import (
    _split_tags,
    build_search_query,
    merge_profile_updates,
    micro_keywords_list,
    normalize_niche_profile,
    profile_from_dict,
)
from aperix_geo.services.competitor.summary import (
    fallback_profile_summary,
    merge_competitors_into_summary,
    replace_summary_section,
)
from aperix_geo.services.crawl.metadata import extract_page_metadata, homepage_metadata_dict
from aperix_geo.utils.text import headings_from_markdown


def test_normalize_profile_micro_niche() -> None:
    profile = normalize_niche_profile(
        {
            "industry": "医疗影像AI诊断与辅助决策系统",
            "core_features": ["AI辅助结节检测", "云端PACS工作流集成", "多余"],
            "target_customers": "三甲医院放射科、医学影像中心",
            "micro_keywords": ["医疗影像AI诊断", "肺结节AI筛查", "云PACS影像系统", "DICOM智能阅片"],
        },
        entity="deepwise.com",
    )
    assert profile["industry"] == "医疗影像AI诊断与辅助决策系统"
    assert "AI辅助结节检测" in profile["core_features"]
    assert profile["core_features"].count("、") <= 2
    assert "肺结节AI筛查" in profile["micro_keywords"]


def test_micro_keywords_list() -> None:
    profile = normalize_niche_profile(
        {
            "industry": "跨境支付",
            "core_features": ["收款"],
            "target_customers": "企业",
            "micro_keywords": ["跨境B2B", "多币种", "企业全球", "国际汇款"],
        },
        entity="example.com",
    )
    assert micro_keywords_list(profile) == ["跨境B2B", "多币种", "企业全球", "国际汇款"]


def test_merge_profile_updates_keywords() -> None:
    base = profile_from_dict(
        {
            "company": "Acme",
            "industry": "SaaS",
            "core_features": "支付",
            "target_customers": "企业",
            "micro_keywords": "旧词一、旧词二",
        },
    )
    merged = merge_profile_updates(base, micro_keywords=["跨境支付", "多币种账户", "企业钱包", "国际汇款"])
    assert "跨境支付" in merged["micro_keywords"]
    assert "旧词一" not in merged["micro_keywords"]


def test_micro_keywords_accepts_five() -> None:
    base = profile_from_dict(
        {
            "company": "Acme",
            "industry": "SaaS",
            "core_features": "支付",
            "target_customers": "企业",
            "micro_keywords": "旧词",
        },
    )
    keywords = ["主题一", "主题二", "主题三", "主题四", "主题五"]
    merged = merge_profile_updates(base, micro_keywords=keywords)
    assert _split_tags(merged["micro_keywords"]) == keywords


def test_micro_keywords_not_truncated() -> None:
    profile = normalize_niche_profile(
        {
            "industry": "跨境支付",
            "core_features": ["收款"],
            "target_customers": "企业",
            "micro_keywords": [
                "跨境B2B收款平台",
                "多币种",
                "企业全球账户系统",
                "国际汇款",
            ],
        },
        entity="example.com",
    )
    parts = _split_tags(profile["micro_keywords"])
    assert parts == [
        "跨境B2B收款平台",
        "多币种",
        "企业全球账户系统",
        "国际汇款",
    ]


def test_search_query_prefers_micro_keywords() -> None:
    profile = normalize_niche_profile(
        {
            "industry": "医疗影像AI诊断与辅助决策系统",
            "core_features": ["AI辅助结节检测"],
            "target_customers": "三甲医院放射科",
            "micro_keywords": ["医疗影像AI诊断", "肺结节AI筛查", "云PACS影像系统", "DICOM智能阅片"],
        },
        entity="deepwise.com",
    )
    q = build_search_query(profile)
    assert q is not None
    assert "医疗影像AI诊断" in q
    assert "肺结节AI筛查" in q


def test_metadata_from_crawl() -> None:
    html = "<head><title>深睿医疗</title><meta name=description content='AI辅助诊断'></head>"
    markdown = "# 用AI赋能\n\n## 改变未来"

    parsed = extract_page_metadata(html=html, markdown=markdown)
    meta = homepage_metadata_dict(parsed)
    assert meta["title"] == "深睿医疗"
    assert headings_from_markdown(markdown) == "用AI赋能 | 改变未来"


def test_fallback_profile_summary_sections() -> None:
    profile = profile_from_dict(
        {
            "company": "示例品牌",
            "industry": "跨境 B2B 支付",
            "core_features": "多币种收款、合规结汇",
            "target_customers": "出海中小企业",
            "micro_keywords": "跨境收款、多币种账户",
        },
    )
    summary = fallback_profile_summary(profile, entity="示例品牌", region_label="中国大陆")
    assert summary.startswith("# 示例品牌")
    assert "## 概述" in summary
    assert "## 竞品" in summary
    assert "## 理想客户画像" in summary
    assert "## 地域与合规" in summary
    assert "典型场景" in summary
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


def test_company_from_setup_session() -> None:
    from unittest.mock import patch

    from aperix_geo.services.setup.helpers import company_from_setup_session

    with patch(
        "aperix_geo.services.setup.helpers.get_session",
        return_value={"profile": {"company": "深睿医疗"}},
    ):
        assert company_from_setup_session(user_id="u1", setup_session_id="abc") == "深睿医疗"

    with patch("aperix_geo.services.setup.helpers.get_session", return_value=None):
        assert company_from_setup_session(user_id="u1", setup_session_id="abc") is None
