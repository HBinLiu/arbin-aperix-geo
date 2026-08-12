"""从 keyword_plan 长尾候选生成监测提示词兜底。"""

from __future__ import annotations

from typing import Any

from aperix_geo.services.competitor.types import NicheProfile
from aperix_geo.services.setup.keyword_plan import (
    KeywordPlan,
    build_keyword_plan,
    match_core_keyword,
    prompt_text_skeleton,
    resolve_topic_core_keyword,
    seed_candidates_from_plan,
)
from aperix_geo.services.prompts.taxonomy import PromptTaxonomyLock

MAX_PROMPT_TEXT_LEN = 28
MIN_SKELETON_LEN = 4

# 与 keyword_plan 长尾模板一一对应（decision, funnel, intent）
_PROMPT_TAG_ROTATION: list[tuple[str, str, str]] = [
    ("scenario_fit", "mofu", "commercial"),
    ("scenario_fit", "mofu", "commercial"),
    ("trust_risk", "mofu", "informational"),
    ("solution_comparison", "bofu", "commercial"),
    ("price_value", "mofu", "commercial"),
]


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
    plan: KeywordPlan,
    limit: int,
    excluded: set[str],
    taxonomy_lock: PromptTaxonomyLock | None = None,
) -> list[dict[str, str]]:
    """用已构建的 keyword_plan 长尾候选生成至多 limit 条提示词。"""
    core = resolve_topic_core_keyword(topic, plan) or ""
    if not core:
        return []

    out: list[dict[str, str]] = []
    seen_text: set[str] = set()
    seen_skeleton: set[str] = set()
    cap = max(1, limit)

    for idx, text in enumerate(
        seed_candidates_from_plan(core, plan=plan, max_len=MAX_PROMPT_TEXT_LEN)
    ):
        if len(out) >= cap:
            break
        body = text.strip()
        if not body or body in seen_text or body in excluded:
            continue
        if not match_core_keyword(body, [core]):
            continue
        skeleton = prompt_text_skeleton(body, core=core)
        sk = skeleton if len(skeleton) >= MIN_SKELETON_LEN else body.casefold()
        if sk in seen_skeleton:
            continue
        seen_text.add(body)
        seen_skeleton.add(sk)
        out.append(_prompt_from_candidate(body, tag_index=idx, taxonomy_lock=taxonomy_lock))

    return out


def build_prompts_from_plan(
    *,
    topics: list[str],
    profile: NicheProfile,
    limit: int,
    excluded: set[str] | None = None,
    taxonomy_lock: PromptTaxonomyLock | None = None,
    plan: KeywordPlan | None = None,
) -> list[dict[str, Any]]:
    blocked = excluded or set()
    keyword_plan = plan or build_keyword_plan(profile)
    return [
        {
            "topic": topic,
            "prompts": build_prompts_for_topic(
                topic=topic,
                plan=keyword_plan,
                limit=limit,
                excluded=blocked,
                taxonomy_lock=taxonomy_lock,
            ),
        }
        for topic in topics
    ]
