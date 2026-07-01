"""八马茶业品牌模式 · 主题生成链路 live 验收（需 DEEPSEEK_API_KEY）。"""

from __future__ import annotations

import json

import pytest

from aperix_geo.config import get_settings
from aperix_geo.services.competitor.profile import search_queries_list, topic_lexicon_dict
from aperix_geo.services.competitor.topic_types import (
    MAX_MONITORING_TOPICS,
    MAX_TOPIC_NAME_LEN,
    MIN_SEED_QUERIES_PER_TOPIC,
)
from aperix_geo.services.setup.llm.stages import run_niche_profile_stage, run_topic_generation_stage
from aperix_geo.services.setup.topic_qa import collect_subject_names, validate_topic_clusters

BAMATEA_BRAND = "八马茶业"
BAMATEA_URL = "https://www.bamatea.com/"
BAMATEA_INTRO = (
    "红茶、岩茶、铁观音中国三大名茶全国销量第一，来自同一个三百年制茶世家——八马茶业，"
    "其源自1723-1736。 八马茶业（6980.HK），作为国家级非物质文化遗产项目乌龙茶制作技艺"
    "（铁观音制作技艺）代表性传承人创立品牌、中华老字号企业、高端中国茶第一股，"
    "公司以“让天下人享受茶的健康与快乐”为使命，以国家级非遗技艺为根基，"
    "以“三大核心品类销量第一”奠定行业领导地位——红茶连续4年全国销量第一，"
    "岩茶连续5年全国销量第一，铁观音连续14年全国销量第一。"
    "旗下八马及信记号品牌分别荣列中国驰名商标及中华老字号。 "
    "线下，八马全国连锁店超3700家，是中国茶叶连锁店第一品牌、高端中国茶全国销量第一品牌； "
    "线上，八马茶业连续11年天猫乌龙茶类目第一，全渠道粉丝超4000万。"
    "八马茶业连续9年入选“中国品牌价值500强”，2024年品牌价值313.59亿元。"
    "2023-2025年，八马连续三年登顶C-CSI中国茶叶连锁店行业顾客满意度第一。"
)

# 品牌模式常见直接竞品（仅用于 topic_plan payload，不测 discover）
BAMATEA_COMPETITORS = [
    {
        "brand": "小罐茶",
        "domain": "xiaoguantea.com",
        "summary": "小罐茶定位高端中国茶，主打礼盒化包装与标准化产品。",
    },
    {
        "brand": "天福茗茶",
        "domain": "tenfu.com",
        "summary": "天福茗茶为连锁茶叶零售品牌，覆盖乌龙茶、红茶等多品类。",
    },
]

# 期望主题与赛道相关的词根（画像或茶行业通用）
_TEA_RELEVANCE_TERMS = (
    "茶",
    "红茶",
    "岩茶",
    "乌龙",
    "铁观音",
    "礼盒",
    "送礼",
    "连锁",
    "高端",
    "非遗",
    "老字号",
    "茶叶",
    "茗茶",
    "品鉴",
    "保存",
    "商务",
    "企业",
    "采购",
)

_FORUM_PREFIXES = ("想问下", "求推荐", "请问", "有没有", "大佬们")


def _deepseek_live_configured() -> bool:
    settings = get_settings()
    return bool(
        settings.deepseek_api_key.strip()
        and settings.deepseek_model.strip()
        and settings.deepseek_base_url.strip()
    )


def _print_topic_report(*, profile: dict, clusters: list[dict]) -> None:
    lexicon = topic_lexicon_dict(profile)
    print("\n[bamatea live] niche profile:")
    print(f"  company={profile.get('company')!r} industry={profile.get('industry')!r}")
    print(f"  features={profile.get('features')!r}")
    print(f"  customers={profile.get('customers')!r}")
    print(f"  topic_lexicon={json.dumps(lexicon, ensure_ascii=False)}")
    print(f"  search_queries={search_queries_list(profile)!r}")
    print("\n[bamatea live] topic clusters:")
    for i, cluster in enumerate(clusters, 1):
        print(f"  {i}. {cluster['name']}")
        for seed in cluster.get("seed_queries") or []:
            print(
                f"     - [{seed['intent']}/{seed['funnel']}/{seed['decision']}] "
                f"{seed['text']}"
            )


def _assert_tea_industry_profile(profile: dict) -> None:
    lexicon = topic_lexicon_dict(profile)
    all_terms = " ".join(
        [
            str(profile.get("industry") or ""),
            str(profile.get("features") or ""),
            str(profile.get("customers") or ""),
            *lexicon.get("category_terms", []),
            *lexicon.get("scenario_terms", []),
            *lexicon.get("audience_terms", []),
            *lexicon.get("pain_terms", []),
        ]
    )
    assert "茶" in all_terms, f"画像应含茶赛道词，实际：{all_terms[:200]}"
    assert search_queries_list(profile), "search_queries 不应为空"


def _assert_topic_content_quality(
    clusters: list[dict],
    *,
    blocked_names: list[str],
    profile: dict,
) -> None:
    blocked_cf = {n.casefold() for n in blocked_names if len(n.strip()) >= 2}
    topic_text_blob = " ".join(c["name"] for c in clusters)
    assert any(term in topic_text_blob for term in _TEA_RELEVANCE_TERMS), (
        f"5 条主题名应贴合茶赛道，实际：{[c['name'] for c in clusters]}"
    )

    lexicon = topic_lexicon_dict(profile)  # type: ignore[arg-type]
    category_terms = [
        t for t in lexicon.get("category_terms", []) if t not in ("茶", "茶叶", "茗茶", "茶业")
    ]
    if category_terms:
        category_hits = sum(
            1
            for cluster in clusters
            if any(term in cluster["name"] for term in category_terms)
        )
        assert category_hits >= 3, (
            f"至少 3 条主题应含 category_terms 品类词根，实际：{[c['name'] for c in clusters]}"
        )

    for cluster in clusters:
        name = cluster["name"]
        assert 2 <= len(name) <= MAX_TOPIC_NAME_LEN

        seeds = cluster.get("seed_queries") or []
        assert MIN_SEED_QUERIES_PER_TOPIC <= len(seeds) <= 8

        for seed in seeds:
            text = seed["text"]
            text_cf = text.casefold()
            for blocked in blocked_cf:
                assert blocked not in text_cf, f"种子问句不得含主体/竞品名「{blocked}」：{text}"
            assert not any(text.startswith(p) for p in _FORUM_PREFIXES), (
                f"种子问句不应含论坛前缀：{text}"
            )
            assert 4 <= len(text) <= 40, f"种子问句长度异常（4–40 字）：{text}"


@pytest.mark.live
@pytest.mark.skipif(
    not _deepseek_live_configured(),
    reason="DEEPSEEK_API_KEY / DEEPSEEK_MODEL / DEEPSEEK_BASE_URL not configured",
)
def test_bamatea_brand_topic_generation_pipeline() -> None:
    """品牌模式：八马茶业资料 → 微观利基画像 → 监测主题规划，验收结构与赛道贴合度。"""
    profile, research, profile_usage = run_niche_profile_stage(
        subject_type="brand",
        target=BAMATEA_BRAND,
        region="CN",
        language="zh-CN",
        website_url=BAMATEA_URL,
        user_corpus=BAMATEA_INTRO,
    )

    assert research["mode"] == "brand"
    assert research["target"] == BAMATEA_BRAND
    assert BAMATEA_INTRO[:20] in research.get("user_corpus", "")
    _assert_tea_industry_profile(profile)

    clusters, topic_usage = run_topic_generation_stage(
        profile=profile,
        subject_type="brand",
        entity_key=BAMATEA_BRAND,
        competitors=BAMATEA_COMPETITORS,
    )

    subject_names = collect_subject_names(
        profile_company=str(profile.get("company") or ""),
        entity_key=BAMATEA_BRAND,
        competitors=BAMATEA_COMPETITORS,
    )
    validate_topic_clusters(clusters, subject_names=subject_names, profile=profile)

    assert len(clusters) == MAX_MONITORING_TOPICS
    assert profile_usage.get("total_tokens", 0) > 0 or profile_usage.get("completion_tokens", 0) > 0
    assert topic_usage.get("total_tokens", 0) > 0 or topic_usage.get("completion_tokens", 0) > 0

    _assert_topic_content_quality(clusters, blocked_names=subject_names, profile=profile)
    _print_topic_report(profile=profile, clusters=clusters)
