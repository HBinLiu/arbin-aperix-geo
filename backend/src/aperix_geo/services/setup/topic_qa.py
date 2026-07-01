"""监测主题簇确定性 QA（LLM 输出后规则校验）。"""

from __future__ import annotations

import re

from aperix_geo.services.competitor.topic_types import (
    MAX_MONITORING_TOPICS,
    MAX_TOPIC_NAME_LEN,
    MIN_SEED_QUERIES_PER_TOPIC,
    TopicCluster,
)
from aperix_geo.services.prompts.taxonomy import FUNNEL_STAGES, SEARCH_INTENTS
from aperix_geo.services.setup.topic_items import topic_name_key

_BRAND_PATTERNS = re.compile(
    r"(chatgpt|deepseek|豆包|kimi|文心|通义|openai|claude|gemini)",
    re.IGNORECASE,
)

# 主题名禁止以决策维度/问法类型命名（决策标签在 Prompt 层）
_DECISION_DIMENSION_MARKERS = (
    "认知",
    "对比",
    "选型",
    "选品",
    "性价比",
    "价格",
    "信任",
    "风险",
    "真伪",
    "口碑",
    "鉴别",
    "怎么选",
    "怎么对比",
    "有哪些",
    "入门",
    "决策",
    "评估",
    "合规",
    "文化体验",
)

_GENERIC_TOPIC_FORBIDDEN = (
    "竞品对比",
    "行业趋势",
    "方案选型",
    "定价决策",
    "口碑评价",
    "品牌信任",
)


def _contains_brand_like(text: str) -> bool:
    return bool(_BRAND_PATTERNS.search(text))


def _decision_dimension_marker(name: str) -> str | None:
    for marker in _DECISION_DIMENSION_MARKERS:
        if marker in name:
            return marker
    return None


def validate_topic_clusters(
    clusters: list[TopicCluster],
    *,
    industry: str,
    lexicon_terms: list[str] | None = None,
) -> None:
    if len(clusters) != MAX_MONITORING_TOPICS:
        raise ValueError(f"监测主题必须恰好 {MAX_MONITORING_TOPICS} 条")

    names: set[str] = set()
    industry_token = industry.strip().casefold()
    unknown_industry = not industry_token or industry_token == "未知行业"
    lexicon = [t.strip() for t in (lexicon_terms or []) if len(t.strip()) >= 2]
    require_industry_specific = bool(lexicon) or not unknown_industry

    for cluster in clusters:
        name = str(cluster.get("name") or "").strip()
        if not name:
            raise ValueError("监测主题名不能为空")
        if len(name) > MAX_TOPIC_NAME_LEN:
            raise ValueError(f"监测主题「{name}」超过 {MAX_TOPIC_NAME_LEN} 字")
        key = topic_name_key(name)
        if key in names:
            raise ValueError(f"监测主题重复：{name}")
        names.add(key)

        if _contains_brand_like(name):
            raise ValueError(f"监测主题不得含平台/品牌名：{name}")

        if name in _GENERIC_TOPIC_FORBIDDEN:
            raise ValueError(f"监测主题过于空泛：{name}")

        marker = _decision_dimension_marker(name)
        if marker:
            raise ValueError(f"监测主题不得按决策维度命名（含「{marker}」）：{name}")

        seeds = cluster.get("seed_queries") or []
        if len(seeds) < MIN_SEED_QUERIES_PER_TOPIC:
            raise ValueError(f"主题「{name}」种子问句不足 {MIN_SEED_QUERIES_PER_TOPIC} 条")

        for seed in seeds:
            text = str(seed.get("text") or "").strip()
            if not text:
                raise ValueError(f"主题「{name}」存在空种子问句")
            funnel = str(seed.get("funnel") or "").strip().lower()
            intent = str(seed.get("intent") or "").strip().lower()
            if funnel not in FUNNEL_STAGES:
                raise ValueError(f"无效 funnel：{funnel}")
            if intent not in SEARCH_INTENTS:
                raise ValueError(f"无效 intent：{intent}")

        if require_industry_specific and not _topic_is_industry_specific(
            name, industry, lexicon
        ):
            label = industry.strip() or "、".join(lexicon[:3])
            raise ValueError(f"监测主题「{name}」未体现行业赛道：{label}")


def _topic_is_industry_specific(name: str, industry: str, lexicon_terms: list[str]) -> bool:
    industry_token = industry.strip().casefold()
    unknown_industry = not industry_token or industry_token == "未知行业"
    candidates: list[str] = []
    if not unknown_industry:
        candidates.append(industry.strip())
    candidates.extend(lexicon_terms)
    for term in candidates:
        token = term.strip()
        if len(token) < 2:
            continue
        if token.casefold() in name.casefold():
            return True
        if _topic_reflects_industry(name, token):
            return True
    return False


def _topic_reflects_industry(name: str, industry: str) -> bool:
    """行业词可能被压缩进主题名；取 industry 中 ≥2 字的连续片段做弱匹配。"""
    name_cf = name.casefold()
    industry = industry.strip()
    if len(industry) < 2:
        return True
    for length in range(min(len(industry), 8), 1, -1):
        for start in range(0, len(industry) - length + 1):
            fragment = industry[start : start + length].casefold()
            if len(fragment) >= 2 and fragment in name_cf:
                return True
    return False
