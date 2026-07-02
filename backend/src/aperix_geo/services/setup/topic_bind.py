"""监测主题 deterministic 绑定：core 对齐 + 从 LLM seed / profile 长尾候选池选取，不模板造句。"""

from __future__ import annotations

import logging

from aperix_geo.services.competitor.topic_types import (
    MAX_MONITORING_TOPICS,
    MIN_SEED_QUERIES_PER_TOPIC,
    SeedQuery,
    TopicCluster,
)
from aperix_geo.services.competitor.types import NicheProfile
from aperix_geo.services.setup.keyword_plan import (
    MIN_TOPIC_CORE_KEYWORDS,
    KeywordPlan,
    build_keyword_plan,
    match_core_keyword,
    match_modifier,
    prompt_text_skeleton,
    seed_candidates_from_plan,
    select_topic_core_keywords,
    topic_modifiers_for_core,
)
from aperix_geo.services.setup.topic_rules import MAX_SEEDS_PER_TOPIC, MAX_SEED_TEXT_LEN, MIN_SEED_TEXT_LEN
from aperix_geo.services.setup.topic_seed import parse_seed

logger = logging.getLogger(__name__)

# 候选长尾默认标签（仅 metadata，问句文案来自 profile）
_CANDIDATE_SEED_TAGS: list[tuple[str, str, str]] = [
    ("scenario_fit", "mofu", "commercial"),
    ("trust_risk", "mofu", "informational"),
    ("solution_comparison", "bofu", "commercial"),
    ("price_value", "mofu", "commercial"),
    ("category_awareness", "tofu", "informational"),
]


def _clip_topic_name(text: str) -> str:
    from aperix_geo.services.competitor.topic_types import MAX_TOPIC_NAME_LEN

    return text.strip()[:MAX_TOPIC_NAME_LEN]


def _seed_skeleton(text: str, *, core: str, plan: KeywordPlan) -> str:
    body = text.strip()
    skeleton = prompt_text_skeleton(body, core=core, modifiers=plan["all_modifiers"])
    return skeleton if len(skeleton) >= 4 else body.casefold()


def _normalize_llm_seed(raw: SeedQuery, *, core: str) -> SeedQuery | None:
    parsed = parse_seed(raw)
    if parsed is None:
        return None
    text = str(parsed.get("text") or "").strip()[:MAX_SEED_TEXT_LEN]
    if len(text) < MIN_SEED_TEXT_LEN:
        return None
    if not match_core_keyword(text, [core]):
        return None
    return SeedQuery(
        text=text,
        intent=str(parsed.get("intent") or "commercial"),
        funnel=str(parsed.get("funnel") or "mofu"),
        decision=str(parsed.get("decision") or "scenario_fit"),
    )


def _candidate_seed(text: str, *, tag_index: int) -> SeedQuery:
    decision, funnel, intent = _CANDIDATE_SEED_TAGS[tag_index % len(_CANDIDATE_SEED_TAGS)]
    return SeedQuery(
        text=text[:MAX_SEED_TEXT_LEN],
        intent=intent,
        funnel=funnel,
        decision=decision,
    )


def _select_seeds_for_core(
    llm_seeds: list[SeedQuery],
    *,
    core: str,
    preferred_modifiers: list[str],
    plan: KeywordPlan,
    topic_index: int,
) -> list[SeedQuery]:
    """LLM seed 优先，不足时从 profile 长尾候选补齐；骨架/决策/修饰词去重。"""
    pool: list[SeedQuery] = []
    pool_keys: set[str] = set()

    def _offer(seed: SeedQuery) -> None:
        text = str(seed.get("text") or "").strip()
        if not text:
            return
        key = text.casefold()
        if key in pool_keys:
            return
        pool_keys.add(key)
        pool.append(seed)

    for raw in llm_seeds:
        normalized = _normalize_llm_seed(raw, core=core)
        if normalized is not None:
            _offer(normalized)

    candidate_texts = seed_candidates_from_plan(
        core,
        plan=plan,
        preferred_modifiers=preferred_modifiers,
        topic_index=topic_index,
        max_len=MAX_SEED_TEXT_LEN,
    )
    for idx, text in enumerate(candidate_texts):
        _offer(_candidate_seed(text, tag_index=idx))

    selected: list[SeedQuery] = []
    seen_text: set[str] = set()
    seen_skeleton: set[str] = set()
    used_decisions: set[str] = set()
    used_modifiers: set[str] = set()

    def _try_take(seed: SeedQuery, *, prefer_new: bool) -> bool:
        if len(selected) >= MIN_SEED_QUERIES_PER_TOPIC:
            return False
        text = str(seed.get("text") or "").strip()
        if not text or text.casefold() in seen_text:
            return False
        sk = _seed_skeleton(text, core=core, plan=plan)
        if sk in seen_skeleton:
            return False
        decision = str(seed.get("decision") or "").strip().lower()
        matched_mod = match_modifier(text, preferred_modifiers)
        mod_key = matched_mod.casefold() if matched_mod else ""
        if prefer_new:
            if decision and decision in used_decisions and mod_key and mod_key in used_modifiers:
                return False
        seen_text.add(text.casefold())
        seen_skeleton.add(sk)
        if decision:
            used_decisions.add(decision)
        if mod_key:
            used_modifiers.add(mod_key)
        selected.append(seed)
        return True

    for seed in pool:
        if len(selected) >= MIN_SEED_QUERIES_PER_TOPIC:
            break
        _try_take(seed, prefer_new=False)

    for seed in pool:
        if len(selected) >= MIN_SEED_QUERIES_PER_TOPIC:
            break
        if str(seed.get("text") or "").strip().casefold() in seen_text:
            continue
        _try_take(seed, prefer_new=True)

    for seed in pool:
        if len(selected) >= MIN_SEED_QUERIES_PER_TOPIC:
            break
        if str(seed.get("text") or "").strip().casefold() in seen_text:
            continue
        _try_take(seed, prefer_new=False)

    if len(selected) < MIN_SEED_QUERIES_PER_TOPIC:
        raise ValueError(
            f"主题「{core}」seed 不足 {MIN_SEED_QUERIES_PER_TOPIC} 条"
            f"（LLM {len(llm_seeds)} 条，profile 候选 {len(candidate_texts)} 条）；"
            f"需补全 search_queries 或 seed LLM 补位"
        )

    if len(used_modifiers) < 2:
        logger.debug(
            "监测主题 bind: 主题「%s」seed 修饰词覆盖 %d 种",
            core,
            len(used_modifiers),
        )

    return selected[:MAX_SEEDS_PER_TOPIC]


def _collect_llm_seeds_for_core(clusters: list[TopicCluster], *, core: str) -> list[SeedQuery]:
    """从全部 topic 簇收集含本 core 的 LLM seed（跨簇汇总，避免错绑簇导致丢 seed）。"""
    out: list[SeedQuery] = []
    seen: set[str] = set()
    for cluster in clusters:
        for raw in cluster.get("seed_queries") or []:
            parsed = parse_seed(raw)
            if parsed is None:
                continue
            text = str(parsed.get("text") or "").strip()
            if not match_core_keyword(text, [core]):
                continue
            key = text.casefold()
            if key in seen:
                continue
            seen.add(key)
            out.append(parsed)
    return out


def bind_topic_clusters_to_cores(
    clusters: list[TopicCluster],
    *,
    profile: NicheProfile,
) -> list[TopicCluster]:
    """将 LLM 簇按核心词重绑：topic name = core_keyword，seed 来自 LLM + profile 候选池。"""
    plan = build_keyword_plan(profile)
    cores = select_topic_core_keywords(profile, count=MAX_MONITORING_TOPICS)
    if len(cores) < MIN_TOPIC_CORE_KEYWORDS:
        raise ValueError(
            f"niche_profile 核心词不足 {MIN_TOPIC_CORE_KEYWORDS} 条（topic 绑定），"
            f"当前 {len(cores)} 条；请回到 Discover 补全 category_terms（至少 5 条）"
        )

    bound: list[TopicCluster] = []
    for idx, core in enumerate(cores):
        topic_name = _clip_topic_name(core)
        preferred = topic_modifiers_for_core(core, plan=plan, topic_index=idx)
        llm_seeds = _collect_llm_seeds_for_core(clusters, core=core)

        bound.append(
            TopicCluster(
                name=topic_name,
                seed_queries=_select_seeds_for_core(
                    llm_seeds,
                    core=core,
                    preferred_modifiers=preferred,
                    plan=plan,
                    topic_index=idx,
                ),
            )
        )
    return bound
