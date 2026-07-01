"""Setup 提示词生成 QA。

硬校验（默认）：结构、枚举、标点、核心词锚定——失败即 400。
质量校验（strict_quality=True）：修饰词、seed 溯源、句式去重、决策覆盖——仅打 warning，避免链路不稳定。
"""

from __future__ import annotations

import logging
import re
from typing import Any

from aperix_geo.services.prompts.taxonomy import FUNNEL_STAGES, SEARCH_INTENTS, normalize_decision_type
from aperix_geo.services.setup.keyword_plan import (
    KeywordPlan,
    build_topic_keyword_map,
    match_core_keyword,
    match_modifier,
    prompt_text_skeleton,
    resolve_topic_core_keyword,
    topic_modifiers_for_core,
)
from aperix_geo.services.setup.topic_items import topic_name_key

logger = logging.getLogger(__name__)

MIN_PROMPT_DECISION_TYPES = 4
MIN_SKELETON_LEN = 4

# 中英文常见标点（监测问句 text 应纯文字，不含标点）
_CN_PUNCT = "，。！？、；：""''（）【】《》…—·"
_ASCII_PUNCT = r",.!?;:'\"()\[\]{}<>/\\@#$%^&*+=~`|-"
_PROMPT_PUNCTUATION_RE = re.compile("[" + re.escape(_CN_PUNCT) + _ASCII_PUNCT + "]")


def strip_prompt_punctuation(text: str) -> str:
    """移除监测问句中的标点，供 Setup 提示词归一化。"""
    return _PROMPT_PUNCTUATION_RE.sub("", (text or "").strip())


def prompt_contains_punctuation(text: str) -> bool:
    return bool(_PROMPT_PUNCTUATION_RE.search(text or ""))


def _prompt_derived_from_seeds(text: str, seed_texts: list[str], *, core: str) -> bool:
    """prompt 须与至少一条 seed 共享除核心词外的语义片段。"""
    body = text.strip()
    if not body or not core:
        return False
    body_cf = body.casefold()
    core_cf = core.casefold()
    for raw in seed_texts:
        seed = str(raw or "").strip()
        if not seed:
            continue
        seed_cf = seed.casefold()
        if seed_cf in body_cf or body_cf in seed_cf:
            return True
        for size in (4, 3):
            if len(seed) < size:
                continue
            for i in range(len(seed) - size + 1):
                piece = seed[i : i + size]
                if len(piece) < 3 or piece.casefold() == core_cf:
                    continue
                if piece.casefold() in body_cf:
                    return True
    return False


def _warn_duplicate_prompt_skeletons(
    items: list[dict[str, Any]],
    *,
    topic_core_map: dict[str, str],
    keyword_plan: KeywordPlan,
) -> None:
    cross_topic: dict[str, set[str]] = {}
    for item in items:
        topic = str(item.get("topic") or "").strip()
        if not topic:
            continue
        topic_key = topic_name_key(topic)
        core = topic_core_map.get(topic_key) or ""
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
            skeleton = prompt_text_skeleton(
                text,
                core=core,
                modifiers=keyword_plan["all_modifiers"],
            )
            if len(skeleton) < MIN_SKELETON_LEN:
                continue
            skeletons.append(skeleton)
            cross_topic.setdefault(skeleton, set()).add(topic)
        if len(skeletons) >= 2 and len(set(skeletons)) == 1:
            logger.warning("监测问句质量: 主题「%s」句式重复", topic)

    for skeleton, topics in cross_topic.items():
        if len(topics) >= 2:
            joined = "、".join(sorted(topics))
            logger.warning("监测问句质量: 跨主题句式重复 %s", joined)


def _reject_duplicate_prompt_skeletons(
    items: list[dict[str, Any]],
    *,
    topic_core_map: dict[str, str],
    keyword_plan: KeywordPlan,
) -> None:
    cross_topic: dict[str, set[str]] = {}
    for item in items:
        topic = str(item.get("topic") or "").strip()
        if not topic:
            continue
        topic_key = topic_name_key(topic)
        core = topic_core_map.get(topic_key) or ""
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
            skeleton = prompt_text_skeleton(
                text,
                core=core,
                modifiers=keyword_plan["all_modifiers"],
            )
            if len(skeleton) < MIN_SKELETON_LEN:
                continue
            skeletons.append(skeleton)
            cross_topic.setdefault(skeleton, set()).add(topic)
        if len(skeletons) >= 2 and len(set(skeletons)) == 1:
            raise ValueError(f"主题「{topic}」监测问句句式重复")

    for skeleton, topics in cross_topic.items():
        if len(topics) >= 2:
            joined = "、".join(sorted(topics))
            raise ValueError(f"监测问句跨主题句式重复：{joined}")


def validate_generated_prompts(
    items: list[dict[str, Any]],
    *,
    keyword_plan: KeywordPlan,
    min_types: int = MIN_PROMPT_DECISION_TYPES,
    topic_clusters: list[dict[str, Any]] | None = None,
    strict_quality: bool = False,
) -> None:
    """校验 Setup 提示词。

    strict_quality=False（默认）：仅硬校验，质量项只打 warning。
    strict_quality=True：启用修饰词/seed 溯源/句式/决策覆盖等全部规则（测试或人工审查用）。
    """
    types: set[str] = set()
    prompt_count = 0
    seeds_by_topic: dict[str, list[str]] = {}
    for cluster in topic_clusters or []:
        if not isinstance(cluster, dict):
            continue
        name = str(cluster.get("name") or "").strip()
        if not name:
            continue
        texts = [
            str(s.get("text") or "").strip()
            for s in (cluster.get("seed_queries") or [])
            if isinstance(s, dict) and str(s.get("text") or "").strip()
        ]
        seeds_by_topic[topic_name_key(name)] = texts

    topic_rows = build_topic_keyword_map(
        [str(i.get("topic") or "") for i in items if str(i.get("topic") or "").strip()],
        plan=keyword_plan,
    )
    topic_core_map: dict[str, str] = {}
    topic_index_map: dict[str, int] = {}
    topic_preferred_map: dict[str, list[str]] = {}
    for idx, row in enumerate(topic_rows):
        key = topic_name_key(str(row.get("topic") or ""))
        topic_core_map[key] = str(row.get("core_keyword") or "")
        topic_index_map[key] = idx
        topic_preferred_map[key] = list(row.get("preferred_modifiers") or [])

    for item in items:
        topic = str(item.get("topic") or "").strip()
        prompts = item.get("prompts")
        if not isinstance(prompts, list):
            raise ValueError(f"主题「{topic or '?'}」缺少 prompts 列表")
        topic_key = topic_name_key(topic)
        core = topic_core_map.get(topic_key) or resolve_topic_core_keyword(topic, keyword_plan)
        preferred = topic_preferred_map.get(topic_key) or topic_modifiers_for_core(
            core or "",
            plan=keyword_plan,
            topic_index=topic_index_map.get(topic_key, 0),
        )
        seed_texts = seeds_by_topic.get(topic_key, [])

        if not core:
            raise ValueError(
                f"主题「{topic}」须完整包含 keyword_plan 核心词之一："
                f"{'、'.join(keyword_plan['core_keywords'][:6])}"
            )

        for row in prompts:
            if not isinstance(row, dict):
                continue
            text = str(row.get("text") or "").strip()
            if not text:
                raise ValueError(f"主题「{topic}」存在空提示词")
            if prompt_contains_punctuation(text):
                raise ValueError(f"监测问句不得含标点符号：{text[:24]}")
            prompt_count += 1
            funnel = str(row.get("funnel_stage") or "").strip().lower()
            intent = str(row.get("search_intent") or "").strip().lower()
            if funnel not in FUNNEL_STAGES:
                raise ValueError(f"无效 funnel：{funnel}")
            if intent not in SEARCH_INTENTS:
                raise ValueError(f"无效 intent：{intent}")
            decision_type = normalize_decision_type(str(row.get("decision_type") or ""))
            if not decision_type:
                raise ValueError(f"提示词缺少 decision_type：{text[:24]}")
            types.add(decision_type)

            if not match_core_keyword(text, [core]):
                raise ValueError(f"监测问句须含主题核心词「{core}」：{text[:24]}")

            if strict_quality:
                if funnel in ("mofu", "bofu") and not match_modifier(text, preferred[:3]):
                    raise ValueError(
                        f"监测问句须含本主题优先修饰词（{'、'.join(preferred[:3])}）：{text[:24]}"
                    )
                if seed_texts:
                    seed_hit = any(
                        strip_prompt_punctuation(text) == strip_prompt_punctuation(s)
                        for s in seed_texts
                    )
                    if not seed_hit and not _prompt_derived_from_seeds(text, seed_texts, core=core):
                        raise ValueError(f"监测问句须由 seed 改写扩展：{text[:24]}")
            else:
                if funnel in ("mofu", "bofu") and not match_modifier(text, preferred[:3]):
                    logger.warning(
                        "监测问句质量: 未命中优先修饰词（%s） topic=%s text=%s",
                        "、".join(preferred[:3]),
                        topic,
                        text[:24],
                    )
                if seed_texts:
                    seed_hit = any(
                        strip_prompt_punctuation(text) == strip_prompt_punctuation(s)
                        for s in seed_texts
                    )
                    if not seed_hit and not _prompt_derived_from_seeds(text, seed_texts, core=core):
                        logger.warning(
                            "监测问句质量: 未由 seed 扩展 topic=%s text=%s",
                            topic,
                            text[:24],
                        )

    if prompt_count == 0:
        raise ValueError("未生成有效提示词")

    required = min(min_types, prompt_count)
    if strict_quality:
        if len(types) < required:
            raise ValueError(f"监测问句须覆盖至少 {required} 种决策类型")
        _reject_duplicate_prompt_skeletons(
            items,
            topic_core_map=topic_core_map,
            keyword_plan=keyword_plan,
        )
    else:
        if len(types) < required:
            logger.warning(
                "监测问句质量: 决策类型仅 %d 种（建议 ≥%d）",
                len(types),
                required,
            )
        _warn_duplicate_prompt_skeletons(
            items,
            topic_core_map=topic_core_map,
            keyword_plan=keyword_plan,
        )
