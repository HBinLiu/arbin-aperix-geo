"""监测主题簇结构校验。

硬校验（默认）：条数、长度、枚举、主体名禁令、核心词锚定。
质量校验（strict_quality=True）：问句形态、泛词、近重复、修饰词、核心词覆盖——仅打 warning。
"""

from __future__ import annotations

import logging
import re
from typing import Any

from aperix_geo.services.competitor.profile import topic_lexicon_dict
from aperix_geo.services.competitor.topic_types import (
    MAX_MONITORING_TOPICS,
    MAX_TOPIC_NAME_LEN,
    MIN_SEED_QUERIES_PER_TOPIC,
    MIN_TOPIC_NAME_LEN,
    SeedQuery,
    TopicCluster,
)
from aperix_geo.services.competitor.types import NicheProfile
from aperix_geo.services.prompts.taxonomy import DECISION_TYPES, FUNNEL_STAGES, SEARCH_INTENTS
from aperix_geo.services.setup.topic_items import topic_name_key
from aperix_geo.services.setup.keyword_plan import (
    build_keyword_plan,
    is_broad_lexicon_term,
    is_modifier_only_category_term,
    match_core_keyword,
    match_modifier,
    resolve_topic_core_keyword,
    select_topic_core_keywords,
    topic_modifiers_for_core,
)
from aperix_geo.services.setup.topic_rules import (
    MAX_SEEDS_PER_TOPIC,
    MIN_CATEGORY_TOPIC_HITS,
)
from aperix_geo.services.setup.keyword_plan import _compact_casefold

logger = logging.getLogger(__name__)

_QUERY_MARKERS = ("?", "？", "怎么", "如何", "哪个", "哪些", "哪家", "为什么", "是否", "多少")
_DECISION_SUFFIX_RE = re.compile(
    r"(?:指南|攻略|排行榜|保障|推荐|对比|比价|选购|选择|性价比)$"
)


def collect_subject_names(
    *,
    profile_company: str = "",
    entity_key: str = "",
    competitors: list[dict[str, Any]] | None = None,
) -> list[str]:
    """从主体与已确认竞品收集动态品牌/域名 token（用于禁令检测）。"""
    tokens: list[str] = []
    seen: set[str] = set()
    for raw in (profile_company, entity_key):
        text = raw.strip()
        if len(text) < 2:
            continue
        key = text.casefold()
        if key in seen:
            continue
        seen.add(key)
        tokens.append(text)
    for item in competitors or []:
        if not isinstance(item, dict):
            continue
        for field in ("brand", "domain", "site_name"):
            text = str(item.get(field) or "").strip()
            if len(text) < 2:
                continue
            key = text.casefold()
            if key in seen:
                continue
            seen.add(key)
            tokens.append(text)
    return tokens


def _contains_subject_name(text: str, subject_names: list[str]) -> str | None:
    text_cf = text.casefold()
    for name in subject_names:
        token = name.strip()
        if len(token) >= 2 and token.casefold() in text_cf:
            return token
    return None


def _validate_seed(seed: SeedQuery, *, topic_name: str, blocked: list[str]) -> None:
    text = str(seed.get("text") or "").strip()
    if not text:
        raise ValueError(f"主题「{topic_name}」存在空种子问句")

    hit = _contains_subject_name(text, blocked)
    if hit:
        raise ValueError(f"种子问句不得含主体/竞品名（含「{hit}」）：{text}")

    funnel = str(seed.get("funnel") or "").strip().lower()
    intent = str(seed.get("intent") or "").strip().lower()
    decision = str(seed.get("decision") or "").strip().lower()
    if funnel not in FUNNEL_STAGES:
        raise ValueError(f"无效 funnel：{funnel}")
    if intent not in SEARCH_INTENTS:
        raise ValueError(f"无效 intent：{intent}")
    if decision not in DECISION_TYPES:
        raise ValueError(f"无效 decision：{decision}")


def _lexicon_terms(profile: NicheProfile) -> list[str]:
    """词表 + features + industry（过滤过宽/过短词根）。"""
    lexicon = topic_lexicon_dict(profile)
    all_terms: list[str] = []
    seen: set[str] = set()
    for key in ("category_terms", "scenario_terms", "audience_terms", "pain_terms"):
        for raw in lexicon.get(key, []):
            term = raw.strip()
            if len(term) < 2 or is_broad_lexicon_term(term, profile):
                continue
            key_cf = term.casefold()
            if key_cf in seen:
                continue
            seen.add(key_cf)
            all_terms.append(term)
    for raw in str(profile.get("features") or "").split("、"):
        term = raw.strip()
        if len(term) < 2 or is_broad_lexicon_term(term, profile):
            continue
        key_cf = term.casefold()
        if key_cf in seen:
            continue
        seen.add(key_cf)
        all_terms.append(term)
    industry = str(profile.get("industry") or "").strip()
    if industry and industry != "未知行业":
        key_cf = industry.casefold()
        if key_cf not in seen:
            seen.add(key_cf)
            all_terms.append(industry)
    return all_terms


def _suffix_covered_by_lexicon(suffix: str, lexicon_terms: list[str]) -> bool:
    suff = suffix.strip()
    if not suff:
        return True
    suff_cf = suff.casefold()
    return any(term.strip().casefold() in suff_cf for term in lexicon_terms if term.strip())


def _unanchored_suffix(name: str, core: str, lexicon_terms: list[str]) -> str | None:
    """core 之后的后缀若无法用词根解释，或呈决策/导购语形态，则视为无效。"""
    idx = name.casefold().find(core.casefold())
    if idx < 0:
        return None
    suffix = name[idx + len(core) :]
    if len(suffix) < 2:
        return None
    if _suffix_covered_by_lexicon(suffix, lexicon_terms):
        return None
    if _DECISION_SUFFIX_RE.search(suffix) or _topic_name_has_query_shape(suffix):
        return suffix
    return suffix


def _topic_name_has_query_shape(name: str) -> bool:
    if any(marker in name for marker in _QUERY_MARKERS):
        return True
    return name.endswith(("吗", "呢"))


def _warn_near_duplicate_topic_names(names: list[str]) -> None:
    compact_names = [(name, _compact_casefold(name)) for name in names]
    for i, (left, lc) in enumerate(compact_names):
        for j, (right, rc) in enumerate(compact_names):
            if i >= j or len(lc) < 2 or len(rc) < 2:
                continue
            if lc in rc or rc in lc:
                logger.warning("监测主题质量: 主题名过于相近 %s / %s", left, right)


def _reject_near_duplicate_topic_names(names: list[str]) -> None:
    compact_names = [(name, _compact_casefold(name)) for name in names]
    for i, (left, lc) in enumerate(compact_names):
        for j, (right, rc) in enumerate(compact_names):
            if i >= j or len(lc) < 2 or len(rc) < 2:
                continue
            if lc in rc or rc in lc:
                raise ValueError(f"监测主题名过于相近：{left} / {right}")


def _reject_generic_standalone_topic(name: str, *, profile: NicheProfile) -> None:
    if is_modifier_only_category_term(name, profile=profile):
        raise ValueError(f"监测主题不得使用场景/对比类泛词：{name}")


def validate_topic_lexicon_precision(
    clusters: list[TopicCluster],
    *,
    profile: NicheProfile,
    strict_quality: bool = False,
) -> None:
    """主题/种子须完整包含核心词；种子修饰词等为质量项。"""
    plan = build_keyword_plan(profile)
    core_keywords = plan["core_keywords"]
    if not core_keywords:
        raise ValueError("niche_profile 缺少可用核心词（category_terms/features）")

    lexicon_terms = _lexicon_terms(profile)
    used_cores: set[str] = set()
    topic_names: list[str] = []
    core_order = select_topic_core_keywords(profile)
    core_index = {term.casefold(): idx for idx, term in enumerate(core_order)}

    for cluster in clusters:
        name = str(cluster.get("name") or "").strip()
        topic_names.append(name)

        if _topic_name_has_query_shape(name):
            msg = f"监测主题名不得采用问句/问法形态：{name}"
            if strict_quality:
                raise ValueError(msg)
            logger.warning("监测主题质量: %s", msg)
        elif is_modifier_only_category_term(name, profile=profile):
            msg = f"监测主题不得使用场景/对比类泛词：{name}"
            if strict_quality:
                raise ValueError(msg)
            logger.warning("监测主题质量: %s", msg)

        core = resolve_topic_core_keyword(name, plan)
        if not core:
            raise ValueError(
                f"监测主题「{name}」须完整包含 keyword_plan 核心词之一："
                f"{'、'.join(core_keywords[:6])}"
            )
        used_cores.add(core.casefold())
        preferred_modifiers = topic_modifiers_for_core(
            core,
            plan=plan,
            topic_index=core_index.get(core.casefold(), 0),
        )

        orphan = _unanchored_suffix(name, core, lexicon_terms)
        if orphan:
            msg = f"监测主题名含未锚定词根「{orphan}」：{name}"
            if strict_quality:
                raise ValueError(msg)
            logger.warning("监测主题质量: %s", msg)

        for seed in cluster.get("seed_queries") or []:
            text = str(seed.get("text") or "").strip()
            if not match_core_keyword(text, [core]):
                raise ValueError(f"种子问句须含本主题核心词「{core}」：{text}")
            if not match_modifier(text, preferred_modifiers):
                msg = (
                    f"种子问句须含本主题优先修饰词（{'、'.join(preferred_modifiers[:3])}）：{text}"
                )
                if strict_quality:
                    raise ValueError(msg)
                logger.warning("监测主题质量: %s", msg)

    if strict_quality:
        _reject_near_duplicate_topic_names(topic_names)
        if len(used_cores) < MAX_MONITORING_TOPICS:
            raise ValueError(
                f"5 条主题须各绑定 1 个不同核心词，实际 {len(used_cores)} 个"
            )
        required = min(MIN_CATEGORY_TOPIC_HITS, len(core_keywords))
        if len(used_cores) < required:
            raise ValueError(
                f"5 条主题须覆盖至少 {required} 个不同核心词，实际 {len(used_cores)} 个"
            )
    else:
        _warn_near_duplicate_topic_names(topic_names)
        if len(used_cores) < MAX_MONITORING_TOPICS:
            logger.warning(
                "监测主题质量: 5 条主题建议各绑定 1 个不同核心词，实际 %d 个",
                len(used_cores),
            )
        required = min(MIN_CATEGORY_TOPIC_HITS, len(core_keywords))
        if len(used_cores) < required:
            logger.warning(
                "监测主题质量: 建议覆盖至少 %d 个不同核心词，实际 %d 个",
                required,
                len(used_cores),
            )


def validate_topic_clusters(
    clusters: list[TopicCluster],
    *,
    profile: NicheProfile,
    subject_names: list[str] | None = None,
    strict_quality: bool = False,
) -> None:
    if len(clusters) != MAX_MONITORING_TOPICS:
        raise ValueError(f"监测主题必须恰好 {MAX_MONITORING_TOPICS} 条")

    blocked = [n.strip() for n in (subject_names or []) if len(n.strip()) >= 2]
    names: set[str] = set()

    for cluster in clusters:
        name = str(cluster.get("name") or "").strip()
        if not name:
            raise ValueError("监测主题名不能为空")
        if len(name) < MIN_TOPIC_NAME_LEN:
            raise ValueError(f"监测主题「{name}」过短（至少 {MIN_TOPIC_NAME_LEN} 字）")
        if len(name) > MAX_TOPIC_NAME_LEN:
            raise ValueError(f"监测主题「{name}」超过 {MAX_TOPIC_NAME_LEN} 字")
        key = topic_name_key(name)
        if key in names:
            raise ValueError(f"监测主题重复：{name}")
        names.add(key)

        hit = _contains_subject_name(name, blocked)
        if hit:
            raise ValueError(f"监测主题不得含主体/竞品名（含「{hit}」）：{name}")

        seeds = cluster.get("seed_queries") or []
        if len(seeds) < MIN_SEED_QUERIES_PER_TOPIC:
            raise ValueError(f"主题「{name}」种子问句不足 {MIN_SEED_QUERIES_PER_TOPIC} 条")
        if len(seeds) > MAX_SEEDS_PER_TOPIC:
            raise ValueError(f"主题「{name}」种子问句超过 {MAX_SEEDS_PER_TOPIC} 条")

        seen_seed_text: set[str] = set()
        for seed in seeds:
            text = str(seed.get("text") or "").strip()
            if text in seen_seed_text:
                raise ValueError(f"主题「{name}」种子问句重复：{text}")
            seen_seed_text.add(text)
            _validate_seed(seed, topic_name=name, blocked=blocked)

    validate_topic_lexicon_precision(clusters, profile=profile, strict_quality=strict_quality)
