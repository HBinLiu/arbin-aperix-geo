"""Tests for topic cluster QA, parse and profile lexicon."""

from __future__ import annotations

import pytest

from aperix_geo.services.competitor.profile import (
    normalize_niche_profile,
    search_queries_list,
    topic_lexicon_dict,
)
from aperix_geo.services.setup.topic_parse import parse_topic_plan_response
from aperix_geo.services.setup.topic_bind import bind_topic_clusters_to_cores
from aperix_geo.services.setup.topic_qa import collect_subject_names, validate_topic_clusters
from aperix_geo.services.setup.profile_qa import sanitize_profile_lexicon


def _bound_validate(
    clusters: list,
    profile: dict,
    *,
    subject_names: list[str] | None = None,
) -> list:
    bound = bind_topic_clusters_to_cores(clusters, profile=profile)
    validate_topic_clusters(bound, subject_names=subject_names, profile=profile)
    return bound


def _minimal_profile(*, entity: str = "test.com") -> dict:
    return normalize_niche_profile(
        {
            "industry": "测试行业",
            "topic_lexicon": {
                "category_terms": ["测试核心词A", "测试核心词B", "测试核心词C", "测试核心词D", "测试核心词E"],
                "scenario_terms": ["测试场景"],
                "audience_terms": ["测试客群"],
                "pain_terms": ["测试痛点"],
            },
            "search_queries": ["测试核心词A测试场景测试客群"],
        },
        entity=entity,
    )


def _seed(text: str, *, dimension: str = "scenario_fit") -> dict[str, str]:
    return {
        "text": text,
        "intent": "commercial",
        "funnel": "mofu",
        "decision": dimension,
    }


def _cluster(name: str, seeds: list[dict[str, str]]) -> dict:
    return {
        "name": name,
        "seed_queries": seeds,
    }


def test_normalize_profile_splits_lexicon_and_search_queries() -> None:
    profile = normalize_niche_profile(
        {
            "industry": "高端绿茶",
            "features": ["礼盒茶"],
            "customers": "企业采购",
            "topic_lexicon": {
                "category_terms": ["高端绿茶", "明前绿茶", "礼盒茶", "春茶礼品", "口粮绿茶"],
                "scenario_terms": ["商务送礼"],
                "audience_terms": ["企业采购"],
                "pain_terms": ["茶叶保存"],
            },
            "search_queries": ["高端绿茶商务送礼", "明前绿茶礼盒采购", "礼盒茶企业采购保存"],
        },
        entity="竹叶青",
    )
    assert "商务送礼" in profile["scenario_terms"]
    assert search_queries_list(profile)[0].startswith("高端绿茶")


def test_parse_topic_plan_response() -> None:
    clusters = parse_topic_plan_response(
        {
            "topic_clusters": [
                _cluster(
                    "商务送礼选茶",
                    [
                        _seed("商务场合送什么茶叶合适"),
                        _seed("商务送礼茶叶怎么选"),
                        _seed("企业送礼选什么茶"),
                    ],
                )
            ]
        }
    )
    assert clusters[0]["name"] == "商务送礼选茶"
    assert len(clusters[0]["seed_queries"]) == 3


def test_validate_topic_clusters_accepts_five_topics() -> None:
    profile = normalize_niche_profile(
        {
            "industry": "高端绿茶",
            "features": ["礼盒茶"],
            "customers": "企业采购",
            "topic_lexicon": {
                "category_terms": ["高端绿茶", "明前绿茶", "礼盒茶", "春茶礼品", "口粮绿茶"],
                "scenario_terms": ["商务送礼"],
                "audience_terms": ["企业采购"],
                "pain_terms": ["茶叶保存"],
            },
            "search_queries": ["高端绿茶商务送礼", "明前绿茶礼盒采购", "礼盒茶企业采购保存"],
        },
        entity="竹叶青",
    )
    clusters = parse_topic_plan_response(
        {
            "topic_clusters": [
                _cluster(
                    "高端绿茶",
                    [
                        _seed("商务送礼高端绿茶怎么选合适"),
                        _seed("企业采购高端绿茶商务送礼"),
                        _seed("高端绿茶商务送礼怎么选"),
                    ],
                ),
                _cluster(
                    "明前绿茶",
                    [
                        _seed("明前绿茶礼盒企业采购", dimension="category_awareness"),
                        _seed("明前绿茶商务送礼怎么选", dimension="category_awareness"),
                        _seed("企业采购明前绿茶礼盒注意什么", dimension="category_awareness"),
                    ],
                ),
                _cluster(
                    "礼盒茶",
                    [
                        _seed("企业采购礼盒茶茶叶保存", dimension="scenario_fit"),
                        _seed("公司年会礼盒茶商务送礼", dimension="scenario_fit"),
                        _seed("批量采购礼盒茶企业采购流程", dimension="scenario_fit"),
                    ],
                ),
                _cluster(
                    "春茶礼品",
                    [
                        _seed("春茶礼品企业采购口粮怎么买", dimension="scenario_fit"),
                        _seed("春茶礼品口粮茶叶保存方法", dimension="scenario_fit"),
                        _seed("企业采购春茶礼品选购", dimension="scenario_fit"),
                    ],
                ),
                _cluster(
                    "口粮绿茶",
                    [
                        _seed("口粮绿茶茶叶保存方法", dimension="trust_risk"),
                        _seed("口粮绿茶企业采购保存注意什么", dimension="trust_risk"),
                        _seed("高档口粮绿茶茶叶保存", dimension="trust_risk"),
                    ],
                ),
            ]
        }
    )
    validate_topic_clusters(clusters, subject_names=["竹叶青"], profile=profile)


def test_validate_rejects_wrong_cluster_count() -> None:
    clusters = parse_topic_plan_response(
        {
            "topic_clusters": [
                _cluster("主题 A", [_seed("问句 A")] * 3),
                _cluster("主题 B", [_seed("问句 B")] * 3),
            ]
        }
    )
    with pytest.raises(ValueError, match="恰好 5"):
        validate_topic_clusters(clusters, profile=_minimal_profile())


def test_validate_rejects_subject_name_in_topic() -> None:
    profile = normalize_niche_profile(
        {
            "industry": "高端绿茶",
            "features": ["礼盒茶"],
            "topic_lexicon": {
                "category_terms": ["高端绿茶", "明前绿茶", "礼盒茶", "春茶礼品", "口粮绿茶"],
                "scenario_terms": ["商务送礼"],
                "audience_terms": ["企业采购"],
                "pain_terms": ["茶叶保存"],
            },
            "search_queries": ["高端绿茶商务送礼", "明前绿茶礼盒采购", "礼盒茶企业采购保存"],
        },
        entity="竹叶青",
    )
    clusters = parse_topic_plan_response(
        {
            "topic_clusters": [
                _cluster(
                    "八马茶业铁观音礼盒",
                    [
                        _seed("商务送礼铁观音礼盒企业采购"),
                        _seed("企业采购铁观音商务送礼"),
                        _seed("铁观音商务送礼怎么选"),
                    ],
                ),
                _cluster(
                    "明前绿茶礼盒",
                    [
                        _seed("明前绿茶礼盒企业采购", dimension="category_awareness"),
                        _seed("明前绿茶商务送礼怎么选", dimension="category_awareness"),
                        _seed("企业采购明前绿茶礼盒", dimension="category_awareness"),
                    ],
                ),
                _cluster(
                    "高端绿茶礼盒",
                    [
                        _seed("企业采购高端绿茶礼盒", dimension="scenario_fit"),
                        _seed("高端绿茶商务送礼礼盒", dimension="scenario_fit"),
                        _seed("高端绿茶礼盒茶叶保存", dimension="scenario_fit"),
                    ],
                ),
                _cluster(
                    "明前绿茶口粮茶",
                    [
                        _seed("明前绿茶企业采购口粮", dimension="scenario_fit"),
                        _seed("明前绿茶口粮茶叶保存", dimension="scenario_fit"),
                        _seed("家庭明前绿茶企业采购", dimension="scenario_fit"),
                    ],
                ),
                _cluster(
                    "礼盒茶茶叶保存",
                    [
                        _seed("礼盒茶茶叶保存方法", dimension="trust_risk"),
                        _seed("礼盒茶企业采购保存", dimension="trust_risk"),
                        _seed("高档礼盒茶茶叶保存", dimension="trust_risk"),
                    ],
                ),
            ]
        }
    )
    with pytest.raises(ValueError, match="主体/竞品名"):
        validate_topic_clusters(clusters, subject_names=["八马茶业"], profile=profile)


def test_validate_rejects_invalid_decision() -> None:
    clusters = parse_topic_plan_response(
        {
            "topic_clusters": [
                _cluster(
                    "主题 A",
                    [
                        _seed("问句一", dimension="unknown_type"),
                        _seed("问句二", dimension="unknown_type"),
                        _seed("问句三", dimension="unknown_type"),
                    ],
                ),
                _cluster("主题 B", [_seed("问句 B1"), _seed("问句 B2"), _seed("问句 B3")]),
                _cluster("主题 C", [_seed("问句 C1"), _seed("问句 C2"), _seed("问句 C3")]),
                _cluster("主题 D", [_seed("问句 D1"), _seed("问句 D2"), _seed("问句 D3")]),
                _cluster("主题 E", [_seed("问句 E1"), _seed("问句 E2"), _seed("问句 E3")]),
            ]
        }
    )
    with pytest.raises(ValueError, match="种子问句不足"):
        validate_topic_clusters(clusters, profile=_minimal_profile())


def test_collect_subject_names_includes_entity_and_competitors() -> None:
    names = collect_subject_names(
        profile_company="八马茶业",
        entity_key="bamatea.com",
        competitors=[{"brand": "小罐茶", "domain": "xiaoguantea.com"}],
    )
    assert "八马茶业" in names
    assert "bamatea.com" in names
    assert "小罐茶" in names


def _bamatea_profile() -> dict:
    return normalize_niche_profile(
        {
            "company": "八马茶业",
            "industry": "高端中国茶连锁",
            "features": ["铁观音", "岩茶", "红茶"],
            "customers": "商务送礼与企业采购",
            "topic_lexicon": {
                "category_terms": ["铁观音", "岩茶", "高端红茶", "茶礼定制", "陈年普洱"],
                "scenario_terms": ["商务送礼", "茶叶礼盒"],
                "audience_terms": ["企业采购", "高端客群"],
                "pain_terms": ["茶叶保存", "礼盒选型"],
            },
            "search_queries": ["高端铁观音商务送礼", "岩茶礼盒企业采购", "高端红茶礼盒选型采购"],
        },
        entity="八马茶业",
    )


def _bamatea_bad_clusters() -> list[dict]:
    return [
        _cluster(
            "茶叶品质保障",
            [_seed("高档茶叶怎么辨别"), _seed("茶叶品质如何看"), _seed("怎么判断茶叶好坏")],
        ),
        _cluster(
            "商务送礼选择",
            [_seed("商务场合送什么茶"), _seed("商务送礼茶叶怎么选"), _seed("企业送礼选什么茶")],
        ),
        _cluster(
            "岩茶选购指南",
            [_seed("岩茶有哪些品种"), _seed("岩茶等级怎么分"), _seed("岩茶怎么挑选")],
        ),
        _cluster(
            "高端红茶推荐",
            [_seed("高端红茶哪个好"), _seed("送礼红茶怎么选"), _seed("高档红茶有哪些")],
        ),
        _cluster(
            "茶叶性价比对比",
            [_seed("茶叶性价比怎么比"), _seed("茶叶价格差在哪"), _seed("同价位茶叶怎么比")],
        ),
    ]


def test_validate_rejects_generic_bamatea_topic_names() -> None:
    profile = _bamatea_profile()
    clusters = parse_topic_plan_response({"topic_clusters": _bamatea_bad_clusters()})
    with pytest.raises(ValueError, match="问句|未锚定|核心词|修饰词"):
        validate_topic_clusters(clusters, subject_names=["八马茶业"], profile=profile, strict_quality=True)


def _geo_saas_profile() -> dict:
    return normalize_niche_profile(
        {
            "company": "AIBase",
            "industry": "GEO监测SaaS",
            "features": ["AI可见度监测", "品牌引用分析"],
            "customers": "市场与增长团队",
            "topic_lexicon": {
                "category_terms": ["AI可见度监测", "品牌搜索可见度", "品牌引用分析", "多平台GEO监测", "GEO品牌监测"],
                "scenario_terms": ["多平台监测", "竞品对标分析"],
                "audience_terms": ["市场团队", "SEO团队"],
                "pain_terms": ["AI引用率", "品牌声量"],
            },
            "search_queries": [
                "AI可见度监测市场团队多平台工具",
                "品牌搜索可见度SEO团队监测方法",
                "品牌引用分析AI引用率怎么算",
                "多平台GEO监测市场团队配置",
                "GEO品牌监测竞品对标差异",
            ],
        },
        entity="aibase.com",
    )


def test_rejects_topic_without_full_core_keyword() -> None:
    profile = _geo_saas_profile()
    clusters = parse_topic_plan_response(
        {
            "topic_clusters": [
                _cluster(
                    "品牌可见度监控",
                    [
                        _seed("AI可见度监测品牌在大模型出现频率"),
                        _seed("AI可见度监测大模型品牌曝光怎么算"),
                        _seed("AI可见度监测AI对话品牌提及次数"),
                    ],
                ),
                _cluster(
                    "AI可见度多平台",
                    [
                        _seed("AI可见度监测AI搜索里品牌曝光怎么算"),
                        _seed("AI可见度监测生成式搜索品牌排名怎么看"),
                        _seed("AI可见度监测AI搜索品牌出现位置"),
                    ],
                ),
                _cluster(
                    "品牌搜索可见度",
                    [
                        _seed("品牌搜索可见度主流AI平台监测怎么做"),
                        _seed("品牌搜索可见度多平台AI引用怎么对比"),
                        _seed("品牌搜索可见度ChatGPT监测差异"),
                    ],
                ),
                _cluster(
                    "品牌引用分析",
                    [
                        _seed("品牌引用分析AI回答引用品牌来源"),
                        _seed("品牌引用分析品牌被AI引用链接怎么查"),
                        _seed("品牌引用分析引用来源域名分布怎么看"),
                    ],
                ),
                _cluster(
                    "竞品对标分析",
                    [
                        _seed("竞品对标分析竞品在AI搜索表现"),
                        _seed("竞品对标分析竞品AI可见度怎么比"),
                        _seed("竞品对标分析对标竞品引用率差异"),
                        _seed("多平台GEO监测主流AI平台监测怎么做"),
                        _seed("多平台GEO监测多平台配置方法"),
                        _seed("多平台GEO监测市场团队品牌曝光统计"),
                        _seed("GEO品牌监测竞品对标分析差异"),
                        _seed("GEO品牌监测市场团队曝光统计"),
                        _seed("GEO品牌监测AI引用率怎么看"),
                    ],
                ),
            ]
        }
    )
    bound = bind_topic_clusters_to_cores(clusters, profile=profile)
    validate_topic_clusters(bound, subject_names=["aibase.com"], profile=profile)


def test_sanitize_profile_demotes_modifier_only_category_terms() -> None:
    profile = normalize_niche_profile(
        {
            "industry": "GEO监测SaaS",
            "features": ["AI可见度监测", "品牌引用分析"],
            "topic_lexicon": {
                "category_terms": ["AI可见度监测", "品牌搜索可见度", "品牌提及率", "品牌提及率分析", "竞品对标"],
                "scenario_terms": ["多平台监测"],
                "audience_terms": ["市场团队"],
                "pain_terms": ["AI引用率"],
            },
            "search_queries": [
                "AI可见度监测市场团队工具",
                "品牌搜索可见度多平台监测",
                "品牌引用分析AI引用率评估",
            ],
        },
        entity="aibase.com",
    )
    cleaned = sanitize_profile_lexicon(profile)
    cats = topic_lexicon_dict(cleaned)["category_terms"]
    assert "竞品对标" not in cleaned["category_terms"]
    assert "竞品对标" in cleaned["scenario_terms"]
    assert "品牌提及率分析" in cats
    assert "品牌提及率" not in cats


def test_bind_topic_clusters_replaces_generic_and_duplicate_names() -> None:
    profile = _geo_saas_profile()
    clusters = parse_topic_plan_response(
        {
            "topic_clusters": [
                _cluster(
                    "GEO监测",
                    [_seed("AI可见度监测市场团队品牌在大模型出现频率"), _seed("AI可见度监测多平台监测怎么做"), _seed("AI可见度监测竞品对标分析差异")],
                ),
                _cluster(
                    "AI品牌可见度",
                    [_seed("品牌搜索可见度市场团队AI搜索品牌曝光怎么算"), _seed("品牌搜索可见度市场团队怎么看"), _seed("品牌搜索可见度SEO团队监测方法")],
                ),
                _cluster(
                    "品牌提及率",
                    [_seed("品牌引用分析AI引用率回答引用品牌来源"), _seed("品牌引用分析AI引用率怎么算"), _seed("品牌引用分析品牌声量变化原因")],
                ),
                _cluster(
                    "品牌提及率分析",
                    [_seed("多平台GEO监测多平台监测主流AI平台怎么做"), _seed("多平台GEO监测多平台监测配置方法"), _seed("多平台GEO监测市场团队品牌曝光统计")],
                ),
                _cluster(
                    "竞品对标",
                    [_seed("竞品对标分析多平台监测表现差异"), _seed("竞品对标分析市场团队AI可见度怎么比"), _seed("竞品对标分析AI引用率差异怎么看"), _seed("GEO品牌监测竞品对标分析差异"), _seed("GEO品牌监测市场团队曝光统计"), _seed("GEO品牌监测AI引用率怎么看")],
                ),
            ]
        }
    )
    bound = bind_topic_clusters_to_cores(clusters, profile=profile)
    names = [c["name"] for c in bound]
    assert "竞品对标" not in names
    assert len(set(names)) == 5
    validate_topic_clusters(bound, subject_names=["aibase.com"], profile=profile)


def test_validate_rejects_near_duplicate_topic_names() -> None:
    profile = normalize_niche_profile(
        {
            "industry": "GEO监测SaaS",
            "features": ["品牌引用分析"],
            "topic_lexicon": {
                "category_terms": [
                    "品牌提及率",
                    "品牌提及率分析",
                    "品牌搜索可见度",
                    "品牌引用分析",
                    "多平台GEO监测",
                ],
                "scenario_terms": ["多平台监测"],
                "audience_terms": ["市场团队"],
                "pain_terms": ["AI引用率"],
            },
            "search_queries": [
                "品牌提及率市场团队多平台监测",
                "品牌搜索可见度多平台监测",
                "品牌引用分析AI引用率评估",
            ],
        },
        entity="aibase.com",
    )
    clusters = parse_topic_plan_response(
        {
            "topic_clusters": [
                _cluster("品牌提及率", [_seed("品牌提及率市场团队多平台监测"), _seed("品牌提及率市场团队怎么选"), _seed("品牌提及率AI引用率评估")]),
                _cluster("品牌提及率分析", [_seed("品牌提及率分析市场团队多平台监测"), _seed("品牌提及率分析市场团队怎么选"), _seed("品牌提及率分析AI引用率评估")]),
                _cluster("品牌搜索可见度", [_seed("品牌搜索可见度市场团队多平台监测"), _seed("品牌搜索可见度市场团队怎么选"), _seed("品牌搜索可见度AI引用率评估")]),
                _cluster("品牌引用分析", [_seed("品牌引用分析市场团队多平台监测"), _seed("品牌引用分析市场团队怎么选"), _seed("品牌引用分析AI引用率评估")]),
                _cluster("多平台GEO监测", [_seed("多平台GEO监测市场团队多平台监测"), _seed("多平台GEO监测市场团队怎么选"), _seed("多平台GEO监测AI引用率评估")]),
            ]
        }
    )
    with pytest.raises(ValueError, match="过于相近"):
        validate_topic_clusters(clusters, subject_names=["aibase.com"], profile=profile, strict_quality=True)


def test_validate_default_tolerates_near_duplicate_topic_names() -> None:
    profile = normalize_niche_profile(
        {
            "industry": "GEO监测SaaS",
            "features": ["品牌引用分析"],
            "topic_lexicon": {
                "category_terms": [
                    "品牌提及率",
                    "品牌提及率分析",
                    "品牌搜索可见度",
                    "品牌引用分析",
                    "多平台GEO监测",
                ],
                "scenario_terms": ["多平台监测"],
                "audience_terms": ["市场团队"],
                "pain_terms": ["AI引用率"],
            },
            "search_queries": [
                "品牌提及率市场团队多平台监测",
                "品牌搜索可见度多平台监测",
                "品牌引用分析AI引用率评估",
            ],
        },
        entity="aibase.com",
    )
    clusters = parse_topic_plan_response(
        {
            "topic_clusters": [
                _cluster("品牌提及率", [_seed("品牌提及率市场团队多平台监测"), _seed("品牌提及率市场团队怎么选"), _seed("品牌提及率AI引用率评估")]),
                _cluster("品牌提及率分析", [_seed("品牌提及率分析市场团队多平台监测"), _seed("品牌提及率分析市场团队怎么选"), _seed("品牌提及率分析AI引用率评估")]),
                _cluster("品牌搜索可见度", [_seed("品牌搜索可见度市场团队多平台监测"), _seed("品牌搜索可见度市场团队怎么选"), _seed("品牌搜索可见度AI引用率评估")]),
                _cluster("品牌引用分析", [_seed("品牌引用分析市场团队多平台监测"), _seed("品牌引用分析市场团队怎么选"), _seed("品牌引用分析AI引用率评估")]),
                _cluster("多平台GEO监测", [_seed("多平台GEO监测市场团队多平台监测"), _seed("多平台GEO监测市场团队怎么选"), _seed("多平台GEO监测AI引用率评估")]),
            ]
        }
    )
    validate_topic_clusters(clusters, subject_names=["aibase.com"], profile=profile)


def test_accepts_core_keyword_topics() -> None:
    profile = _geo_saas_profile()
    clusters = parse_topic_plan_response(
        {
            "topic_clusters": [
                _cluster(
                    "AI可见度监测",
                    [
                        _seed("AI可见度监测市场团队品牌在大模型出现频率"),
                        _seed("AI可见度监测多平台监测怎么做"),
                        _seed("AI可见度监测竞品对标分析差异"),
                    ],
                ),
                _cluster(
                    "品牌搜索可见度",
                    [
                        _seed("品牌搜索可见度市场团队AI搜索品牌曝光怎么算"),
                        _seed("品牌搜索可见度市场团队怎么看"),
                        _seed("品牌搜索可见度SEO团队监测方法"),
                    ],
                ),
                _cluster(
                    "品牌引用分析",
                    [
                        _seed("品牌引用分析AI引用率回答引用品牌来源"),
                        _seed("品牌引用分析AI引用率怎么算"),
                        _seed("品牌引用分析品牌声量变化原因"),
                    ],
                ),
                _cluster(
                    "多平台GEO监测",
                    [
                        _seed("多平台GEO监测多平台监测主流AI平台怎么做"),
                        _seed("多平台GEO监测多平台监测配置方法"),
                        _seed("多平台GEO监测市场团队品牌曝光统计"),
                    ],
                ),
                _cluster(
                    "GEO品牌监测",
                    [
                        _seed("GEO品牌监测多平台监测表现差异"),
                        _seed("GEO品牌监测市场团队AI可见度怎么比"),
                        _seed("GEO品牌监测AI引用率差异怎么看"),
                    ],
                ),
            ]
        }
    )
    _bound_validate(clusters, profile, subject_names=["aibase.com"])


def test_rejects_topic_name_over_max_len() -> None:
    profile = _geo_saas_profile()
    clusters = parse_topic_plan_response(
        {
            "topic_clusters": [
                _cluster(
                    "AI可见度监测竞品对标分析",
                    [
                        _seed("AI可见度监测品牌在大模型出现频率"),
                        _seed("AI可见度监测多平台监测怎么做"),
                        _seed("AI可见度监测竞品对标分析差异"),
                    ],
                ),
                _cluster(
                    "品牌搜索可见度",
                    [
                        _seed("品牌搜索可见度AI搜索里品牌曝光怎么算"),
                        _seed("品牌搜索可见度市场团队怎么看"),
                        _seed("品牌搜索可见度SEO团队监测方法"),
                    ],
                ),
                _cluster(
                    "品牌引用分析",
                    [
                        _seed("品牌引用分析AI回答引用品牌来源"),
                        _seed("品牌引用分析AI引用率怎么算"),
                        _seed("品牌引用分析品牌声量变化原因"),
                    ],
                ),
                _cluster(
                    "AI可见度监测平台",
                    [
                        _seed("AI可见度监测主流AI平台监测怎么做"),
                        _seed("AI可见度监测多平台监测配置方法"),
                        _seed("AI可见度监测市场团队品牌曝光统计"),
                    ],
                ),
                _cluster(
                    "AI可见度监测对标",
                    [
                        _seed("AI可见度监测竞品对标分析表现"),
                        _seed("AI可见度监测竞品AI可见度怎么比"),
                        _seed("AI可见度监测对标竞品引用率差异"),
                    ],
                ),
            ]
        }
    )
    with pytest.raises(ValueError, match="超过 12 字"):
        validate_topic_clusters(clusters, subject_names=["aibase.com"], profile=profile)


def test_rejects_unanchored_topic_name() -> None:
    profile = _geo_saas_profile()
    clusters = parse_topic_plan_response(
        {
            "topic_clusters": [
                _cluster(
                    "品牌心智份额",
                    [
                        _seed("心智份额怎么量化"),
                        _seed("品牌心智占有率指标"),
                        _seed("心智份额和声量区别"),
                    ],
                ),
                _cluster(
                    "AI搜索可见度",
                    [
                        _seed("AI搜索里品牌曝光怎么算"),
                        _seed("生成式搜索品牌排名怎么看"),
                        _seed("AI搜索品牌出现位置"),
                    ],
                ),
                _cluster(
                    "多平台GEO监测",
                    [
                        _seed("主流AI平台监测怎么做"),
                        _seed("多平台AI引用怎么对比"),
                        _seed("ChatGPT和Perplexity监测差异"),
                    ],
                ),
                _cluster(
                    "品牌引用分析",
                    [
                        _seed("AI回答引用品牌来源"),
                        _seed("品牌被AI引用链接怎么查"),
                        _seed("引用来源域名分布怎么看"),
                    ],
                ),
                _cluster(
                    "竞品对标场景",
                    [
                        _seed("竞品在AI搜索表现"),
                        _seed("竞品AI可见度怎么比"),
                        _seed("对标竞品引用率差异"),
                    ],
                ),
            ]
        }
    )
    with pytest.raises(ValueError, match="完整包含 keyword_plan 核心词"):
        validate_topic_clusters(clusters, subject_names=["aibase.com"], profile=profile)


def test_validate_accepts_precise_bamatea_topic_names() -> None:
    profile = _bamatea_profile()
    clusters = parse_topic_plan_response(
        {
            "topic_clusters": [
                _cluster(
                    "铁观音",
                    [
                        _seed("商务送礼铁观音怎么选合适"),
                        _seed("商务送礼选铁观音还是岩茶"),
                        _seed("企业采购送客户铁观音怎么选"),
                    ],
                ),
                _cluster(
                    "岩茶",
                    [
                        _seed("岩茶礼盒企业采购适合送客户吗"),
                        _seed("商务送礼岩茶礼品怎么搭配"),
                        _seed("岩茶礼盒选型有哪些规格"),
                    ],
                ),
                _cluster(
                    "高端红茶",
                    [
                        _seed("高端红茶礼盒企业采购怎么选"),
                        _seed("商务送礼高端红茶礼盒有哪些档次"),
                        _seed("企业采购高端红茶礼盒注意什么"),
                    ],
                ),
                _cluster(
                    "陈年普洱",
                    [
                        _seed("陈年普洱企业采购渠道怎么选"),
                        _seed("陈年普洱商务送礼选购注意什么"),
                        _seed("陈年普洱茶叶保存方法有哪些"),
                    ],
                ),
                _cluster(
                    "茶礼定制",
                    [
                        _seed("茶礼定制与企业采购传承"),
                        _seed("茶礼定制礼盒选型区别"),
                        _seed("茶礼定制茶叶保存要点"),
                    ],
                ),
            ]
        }
    )
    validate_topic_clusters(clusters, subject_names=["八马茶业"], profile=profile)
