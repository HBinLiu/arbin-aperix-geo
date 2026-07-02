"""Setup 问句风格 LLM 软评（替代语气词表 hard fail）。"""

from __future__ import annotations

import json
import logging
from typing import Any, Literal

from aperix_geo.services.competitor.topic_types import TopicCluster
from aperix_geo.services.providers import chat_completion
from aperix_geo.services.providers.prompts import (
    QUERY_STYLE_JUDGE_SYSTEM,
    QUERY_STYLE_JUDGE_USER_SUFFIX,
)
from aperix_geo.services.setup.keyword_plan import KeywordPlan
from aperix_geo.utils.json import extract_json_object

logger = logging.getLogger(__name__)

StyleStage = Literal["profile", "topics", "prompts"]


def style_groups_for_profile(*, plan: KeywordPlan) -> list[dict[str, Any]]:
    queries = [q.strip() for q in plan["long_tail_examples"] if q.strip()]
    if not queries:
        return []
    return [{"label": "search_queries", "queries": queries}]


def style_groups_for_topics(clusters: list[TopicCluster]) -> list[dict[str, Any]]:
    groups: list[dict[str, Any]] = []
    for cluster in clusters:
        name = str(cluster.get("name") or "").strip()
        texts = [
            str(seed.get("text") or "").strip()
            for seed in (cluster.get("seed_queries") or [])
            if isinstance(seed, dict) and str(seed.get("text") or "").strip()
        ]
        if not texts:
            continue
        groups.append({"label": "seed_queries", "topic": name, "queries": texts})
    return groups


def style_groups_for_prompts(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: list[dict[str, Any]] = []
    for item in items:
        topic = str(item.get("topic") or "").strip()
        prompts = item.get("prompts")
        if not topic or not isinstance(prompts, list):
            continue
        texts = [
            str(row.get("text") or "").strip()
            for row in prompts
            if isinstance(row, dict) and str(row.get("text") or "").strip()
        ]
        if not texts:
            continue
        groups.append({"label": "prompts", "topic": topic, "queries": texts})
    return groups


def evaluate_query_style_via_llm(
    *,
    stage: StyleStage,
    groups: list[dict[str, Any]],
    long_tail_examples: list[str] | None = None,
    entity_key: str = "",
    temperature: float = 0.0,
) -> tuple[list[str], dict[str, Any]]:
    """LLM 软评问句风格。返回 (feedback 行, usage)；feedback 空表示通过。"""
    cleaned_groups = []
    for group in groups:
        queries = [q.strip() for q in group.get("queries") or [] if str(q).strip()]
        if not queries:
            continue
        cleaned_groups.append({**group, "queries": queries})
    if not cleaned_groups:
        return [], {}

    payload: dict[str, Any] = {
        "stage": stage,
        "entity_key": entity_key.strip(),
        "groups": cleaned_groups,
    }
    examples = [q.strip() for q in (long_tail_examples or []) if str(q).strip()]
    if examples:
        payload["long_tail_examples"] = examples

    text, usage, latency_ms = chat_completion(
        [
            {"role": "system", "content": QUERY_STYLE_JUDGE_SYSTEM},
            {
                "role": "user",
                "content": (
                    f"{json.dumps(payload, ensure_ascii=False, indent=2)}\n\n"
                    f"{QUERY_STYLE_JUDGE_USER_SUFFIX}"
                ),
            },
        ],
        temperature=temperature,
        json_mode=True,
    )
    data = extract_json_object(text)
    passed = bool(data.get("pass"))
    raw_feedback = data.get("feedback")
    feedback: list[str] = []
    if isinstance(raw_feedback, list):
        feedback = [str(line).strip() for line in raw_feedback if str(line).strip()]
    elif isinstance(raw_feedback, str) and raw_feedback.strip():
        feedback = [raw_feedback.strip()]

    if passed or not feedback:
        logger.debug(
            "Setup 问句风格软评通过 stage=%s entity=%r (%dms)",
            stage,
            entity_key,
            latency_ms,
        )
        return [], usage

    logger.debug(
        "Setup 问句风格软评未通过 stage=%s entity=%r items=%d (%dms)",
        stage,
        entity_key,
        len(feedback),
        latency_ms,
    )
    return feedback[:8], usage
