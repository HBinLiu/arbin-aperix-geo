"""从 topic seed_queries + profile 长尾候选生成监测提示词，不拼后缀、不用固定问句模板。"""

from __future__ import annotations

from typing import Any

from aperix_geo.services.competitor.types import NicheProfile
from aperix_geo.services.setup.keyword_plan import (
    KeywordPlan,
    build_keyword_plan,
    build_topic_keyword_map,
    match_core_keyword,
    prompt_text_skeleton,
    seed_candidates_from_plan,
    topic_modifiers_for_core,
)
from aperix_geo.services.setup.topic_items import topic_name_key
from aperix_geo.services.setup.topic_seed import parse_seed
from aperix_geo.services.prompts.taxonomy import PromptTaxonomyLock

MAX_PROMPT_TEXT_LEN = 28
MIN_SKELETON_LEN = 4

_PROMPT_TAG_ROTATION: list[tuple[str, str, str]] = [
    ("scenario_fit", "mofu", "commercial"),
    ("trust_risk", "mofu", "informational"),
    ("solution_comparison", "bofu", "commercial"),
    ("price_value", "mofu", "commercial"),
    ("category_awareness", "tofu", "informational"),
    ("scenario_fit", "tofu", "informational"),
    ("trust_risk", "bofu", "informational"),
    ("solution_comparison", "mofu", "commercial"),
    ("price_value", "bofu", "commercial"),
    ("category_awareness", "mofu", "informational"),
]


def _cluster_for_topic(
    topic: str,
    topic_clusters: list[dict[str, Any]] | None,
) -> dict[str, Any] | None:
    key = topic_name_key(topic)
    for cluster in topic_clusters or []:
        if not isinstance(cluster, dict):
            continue
        name = str(cluster.get("name") or "").strip()
        if name and topic_name_key(name) == key:
            return cluster
    return None


def _skeleton_key(text: str, *, core: str, plan: KeywordPlan) -> str:
    body = text.strip()
    skeleton = prompt_text_skeleton(body, core=core, modifiers=plan["all_modifiers"])
    return skeleton if len(skeleton) >= MIN_SKELETON_LEN else body.casefold()


def _prompt_from_seed(
    seed: dict[str, str],
    *,
    taxonomy_lock: PromptTaxonomyLock | None = None,
) -> dict[str, str]:
    from aperix_geo.services.prompts.taxonomy import (
        normalize_decision_type,
        normalize_funnel_stage,
        normalize_search_intent,
    )

    row = {
        "text": str(seed.get("text") or "").strip()[:MAX_PROMPT_TEXT_LEN],
        "funnel_stage": normalize_funnel_stage(str(seed.get("funnel") or "")),
        "search_intent": normalize_search_intent(str(seed.get("intent") or "")),
        "decision_type": normalize_decision_type(str(seed.get("decision") or "")) or "scenario_fit",
    }
    return taxonomy_lock.apply_prompt_row(row) if taxonomy_lock is not None else row


def _prompt_from_candidate(
    text: str,
    *,
    tag_index: int,
    taxonomy_lock: PromptTaxonomyLock | None = None,
) -> dict[str, str]:
    decision, funnel, intent = _PROMPT_TAG_ROTATION[tag_index % len(_PROMPT_TAG_ROTATION)]
    row = {
        "text": text.strip()[:MAX_PROMPT_TEXT_LEN],
        "funnel_stage": funnel,
        "search_intent": intent,
        "decision_type": decision,
    }
    return taxonomy_lock.apply_prompt_row(row) if taxonomy_lock is not None else row


def build_prompts_for_topic(
    *,
    topic: str,
    topic_clusters: list[dict[str, Any]] | None,
    profile: NicheProfile,
    topic_index: int,
    limit: int,
    excluded: set[str],
    taxonomy_lock: PromptTaxonomyLock | None = None,
) -> list[dict[str, str]]:
    """seed 1:1 转 prompt，再用 profile 长尾候选扩展至 limit 条。"""
    plan = build_keyword_plan(profile)
    rows = build_topic_keyword_map([topic], plan=plan)
    core = str(rows[0].get("core_keyword") or "") if rows else ""
    if not core:
        return []

    cluster = _cluster_for_topic(topic, topic_clusters)
    seeds = []
    for raw in (cluster or {}).get("seed_queries") or []:
        seed = parse_seed(raw)
        if seed is not None:
            seeds.append(seed)

    preferred = topic_modifiers_for_core(core, plan=plan, topic_index=topic_index)

    out: list[dict[str, str]] = []
    seen_text: set[str] = set()
    seen_skeleton: set[str] = set()
    cap = max(1, limit)

    def try_add_row(row: dict[str, str]) -> bool:
        if len(out) >= cap:
            return False
        body = str(row.get("text") or "").strip()
        if not body or body in seen_text or body in excluded:
            return False
        if not match_core_keyword(body, [core]):
            return False
        sk = _skeleton_key(body, core=core, plan=plan)
        if sk in seen_skeleton:
            return False
        seen_text.add(body)
        seen_skeleton.add(sk)
        out.append(row)
        return True

    for seed in seeds:
        try_add_row(_prompt_from_seed(seed, taxonomy_lock=taxonomy_lock))

    for idx, text in enumerate(
        seed_candidates_from_plan(
            core,
            plan=plan,
            preferred_modifiers=preferred,
            topic_index=topic_index,
            max_len=MAX_PROMPT_TEXT_LEN,
        )
    ):
        if len(out) >= cap:
            break
        try_add_row(_prompt_from_candidate(text, tag_index=idx, taxonomy_lock=taxonomy_lock))

    return out


def build_prompts_from_seeds(
    *,
    topics: list[str],
    topic_clusters: list[dict[str, Any]] | None,
    profile: NicheProfile,
    limit: int,
    excluded: set[str] | None = None,
    taxonomy_lock: PromptTaxonomyLock | None = None,
) -> list[dict[str, Any]]:
    blocked = excluded or set()
    return [
        {
            "topic": topic,
            "prompts": build_prompts_for_topic(
                topic=topic,
                topic_clusters=topic_clusters,
                profile=profile,
                topic_index=idx,
                limit=limit,
                excluded=blocked,
                taxonomy_lock=taxonomy_lock,
            ),
        }
        for idx, topic in enumerate(topics)
    ]
