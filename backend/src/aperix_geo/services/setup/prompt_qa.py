"""Setup 提示词 QA。

默认：归一化后的结构校验（非空 text + 合法 funnel/intent/decision）。
strict_quality：额外核心词锚定 / 决策覆盖 / 句式去重（测试与审查）。
"""

from __future__ import annotations

from typing import Any

from aperix_geo.services.prompts.taxonomy import FUNNEL_STAGES, SEARCH_INTENTS, normalize_decision_type
from aperix_geo.services.setup.keyword_plan import (
    KeywordPlan,
    match_core_keyword,
    prompt_text_skeleton,
    resolve_topic_core_keyword,
)
from aperix_geo.services.setup.topic_items import topic_name_key

MIN_PROMPT_DECISION_TYPES = 4
MIN_SKELETON_LEN = 4


def _reject_duplicate_prompt_skeletons(
    items: list[dict[str, Any]],
    *,
    topic_core_map: dict[str, str],
) -> None:
    cross_topic: dict[str, set[str]] = {}
    for item in items:
        topic = str(item.get("topic") or "").strip()
        if not topic:
            continue
        core = topic_core_map.get(topic_name_key(topic)) or ""
        prompts = item.get("prompts")
        if not isinstance(prompts, list):
            continue
        skeletons: list[str] = []
        for row in prompts:
            if not isinstance(row, dict):
                continue
            text = str(row.get("text") or "").strip()
            if not text or not core:
                continue
            skeleton = prompt_text_skeleton(text, core=core)
            if len(skeleton) < MIN_SKELETON_LEN:
                continue
            skeletons.append(skeleton)
            cross_topic.setdefault(skeleton, set()).add(topic)
        if len(skeletons) >= 2 and len(set(skeletons)) == 1:
            raise ValueError(f"主题「{topic}」监测问句句式重复")

    for _skeleton, topics in cross_topic.items():
        if len(topics) >= 2:
            raise ValueError(f"监测问句跨主题句式重复：{'、'.join(sorted(topics))}")


def validate_generated_prompts(
    items: list[dict[str, Any]],
    *,
    keyword_plan: KeywordPlan | None = None,
    min_types: int = MIN_PROMPT_DECISION_TYPES,
    strict_quality: bool = False,
) -> None:
    """校验 Setup 提示词批次。

    默认只验结构。strict_quality 需要 keyword_plan。
    """
    if strict_quality and keyword_plan is None:
        raise ValueError("strict_quality 需要 keyword_plan")

    types: set[str] = set()
    prompt_count = 0
    topic_core_map: dict[str, str] = {}
    if strict_quality and keyword_plan is not None:
        for item in items:
            topic = str(item.get("topic") or "").strip()
            if not topic:
                continue
            topic_core_map[topic_name_key(topic)] = (
                resolve_topic_core_keyword(topic, keyword_plan) or ""
            )

    for item in items:
        topic = str(item.get("topic") or "").strip()
        prompts = item.get("prompts")
        if not isinstance(prompts, list):
            raise ValueError(f"主题「{topic or '?'}」缺少 prompts 列表")

        core = ""
        if strict_quality:
            core = topic_core_map.get(topic_name_key(topic)) or ""
            if not core:
                cores = (keyword_plan or {}).get("core_keywords") or []
                raise ValueError(
                    f"主题「{topic}」须完整包含 keyword_plan 核心词之一："
                    f"{'、'.join(cores[:6])}"
                )

        for row in prompts:
            if not isinstance(row, dict):
                continue
            text = str(row.get("text") or "").strip()
            if not text:
                raise ValueError(f"主题「{topic}」存在空提示词")
            prompt_count += 1
            funnel = str(row.get("funnel_stage") or "").strip().lower()
            intent = str(row.get("search_intent") or "").strip().lower()
            if funnel not in FUNNEL_STAGES:
                raise ValueError(f"无效 funnel：{funnel}")
            if intent not in SEARCH_INTENTS:
                raise ValueError(f"无效 intent：{intent}")
            if strict_quality:
                decision_type = normalize_decision_type(str(row.get("decision_type") or ""))
                types.add(decision_type)
                if core and not match_core_keyword(text, [core]):
                    raise ValueError(f"监测问句须含主题核心词「{core}」：{text[:24]}")

    if prompt_count == 0:
        raise ValueError("未生成有效提示词")

    if strict_quality:
        required = min(min_types, prompt_count)
        if len(types) < required:
            raise ValueError(f"监测问句须覆盖至少 {required} 种决策类型")
        _reject_duplicate_prompt_skeletons(items, topic_core_map=topic_core_map)
