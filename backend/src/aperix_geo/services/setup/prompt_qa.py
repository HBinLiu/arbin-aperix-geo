"""Setup 提示词生成 QA（intent × funnel × decision_type）。"""

from __future__ import annotations

from typing import Any

from aperix_geo.services.setup.decision_type import normalize_decision_type
from aperix_geo.services.prompts.taxonomy import FUNNEL_STAGES, SEARCH_INTENTS

MIN_PROMPT_DECISION_TYPES = 4


def validate_generated_prompts(
    items: list[dict[str, Any]],
    *,
    min_types: int = MIN_PROMPT_DECISION_TYPES,
) -> None:
    """校验 Setup 生成的提示词组合：每条标签合法，全库 decision_type 覆盖足够。"""
    types: set[str] = set()
    prompt_count = 0
    for item in items:
        topic = str(item.get("topic") or "").strip()
        prompts = item.get("prompts")
        if not isinstance(prompts, list):
            raise ValueError(f"主题「{topic or '?'}」缺少 prompts 列表")
        for row in prompts:
            if not isinstance(row, dict):
                continue
            text = str(row.get("text") or "").strip()
            if not text:
                raise ValueError(f"主题「{topic}」存在空提示词")
            prompt_count += 1
            funnel = str(row.get("funnel_stage") or row.get("funnel") or "").strip().lower()
            intent = str(row.get("search_intent") or row.get("intent") or "").strip().lower()
            if funnel not in FUNNEL_STAGES:
                raise ValueError(f"无效 funnel：{funnel}")
            if intent not in SEARCH_INTENTS:
                raise ValueError(f"无效 intent：{intent}")
            decision_type = normalize_decision_type(str(row.get("decision_type") or ""))
            if not decision_type:
                raise ValueError(f"提示词缺少 decision_type：{text[:24]}")
            types.add(decision_type)

    if prompt_count == 0:
        raise ValueError("未生成有效提示词")

    required = min(min_types, prompt_count)
    if len(types) < required:
        raise ValueError(f"监测问句须覆盖至少 {required} 种决策类型")
