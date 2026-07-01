"""Seed query 归一化：LLM JSON ↔ TopicCluster 内部结构。"""

from __future__ import annotations

from typing import Any

from aperix_geo.services.competitor.topic_types import SeedQuery
from aperix_geo.services.prompts.taxonomy import normalize_funnel_stage, normalize_search_intent
from aperix_geo.services.prompts.taxonomy import normalize_decision


def parse_seed(raw: Any) -> SeedQuery | None:
    """LLM / session 单条 seed → 归一化 SeedQuery；无效 decision 等返回 None。"""
    if not isinstance(raw, dict):
        return None
    text = str(raw.get("text") or "").strip()
    if not text:
        return None
    decision = normalize_decision(str(raw.get("decision") or ""))
    if not decision:
        return None
    return SeedQuery(
        text=text,
        intent=normalize_search_intent(str(raw.get("intent") or "")),
        funnel=normalize_funnel_stage(str(raw.get("funnel") or "")),
        decision=decision,
    )


def seed_to_llm_dict(seed: SeedQuery) -> dict[str, str]:
    """内部 SeedQuery → Prompts 步 LLM user payload。"""
    return {
        "text": seed["text"],
        "intent": seed["intent"],
        "funnel": seed["funnel"],
        "decision": seed["decision"],
    }
