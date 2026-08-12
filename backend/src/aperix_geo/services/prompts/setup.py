"""设置向导：初始提示词生成（LLM 主路径，keyword_plan 补齐/兜底）。"""

from __future__ import annotations

import hashlib
import json
import logging
from collections.abc import Callable
from typing import Any

from aperix_geo.services.competitor.profile import keywords_list
from aperix_geo.services.competitor.types import NicheProfile
from aperix_geo.services.providers import LLMProviderError, chat_completion
from aperix_geo.services.providers.prompts import (
    SETUP_WIZARD_PROMPTS_USER_PREFIX,
    setup_wizard_prompts_system,
)
from aperix_geo.services.prompts.constants import PROMPT_MAX_PER_TOPIC, PROMPT_PER_TOPIC
from aperix_geo.services.prompts.taxonomy import (
    PromptTaxonomyLock,
    normalize_decision_type,
    normalize_funnel_stage,
    normalize_search_intent,
)
from aperix_geo.services.setup.keyword_plan import KeywordPlan, build_keyword_plan
from aperix_geo.services.setup.prompt_qa import validate_generated_prompts
from aperix_geo.services.setup.prompt_seed import build_prompts_from_plan
from aperix_geo.services.setup.topic_items import topic_name_key
from aperix_geo.utils.json import extract_json_object

logger = logging.getLogger(__name__)


def llm_prompt_row_to_internal(
    item: dict[str, Any],
    *,
    taxonomy_lock: PromptTaxonomyLock | None = None,
) -> dict[str, str] | None:
    """LLM 短字段 → 内部长字段；可选 taxonomy lock。"""
    text = str(item.get("text") or "").strip()
    if not text:
        return None
    row = {
        "text": text,
        "funnel_stage": normalize_funnel_stage(str(item.get("funnel") or "")),
        "search_intent": normalize_search_intent(str(item.get("intent") or "")),
        "decision_type": normalize_decision_type(str(item.get("decision") or "")),
    }
    return taxonomy_lock.apply_prompt_row(row) if taxonomy_lock is not None else row


def _normalize_generated_prompts(
    raw: list[Any],
    *,
    limit: int,
    excluded: set[str],
    taxonomy_lock: PromptTaxonomyLock | None = None,
) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in raw:
        if not isinstance(item, dict):
            continue
        row = llm_prompt_row_to_internal(item, taxonomy_lock=taxonomy_lock)
        if row is None:
            continue
        text = row["text"]
        if text in seen or text in excluded:
            continue
        seen.add(text)
        out.append(row)
        if len(out) >= limit:
            break
    return out


def _build_user_payload(
    *,
    entity: str,
    topics: list[str],
    competitors: list[str],
    aliases: list[str],
    prompts_per_topic: int,
    exclude_prompts: list[str],
    profile: NicheProfile,
    taxonomy_lock: PromptTaxonomyLock | None = None,
) -> dict[str, Any]:
    n = max(1, min(int(prompts_per_topic), PROMPT_MAX_PER_TOPIC))
    payload: dict[str, Any] = {
        "entity": entity.strip() or "本品牌",
        "aliases": [a.strip() for a in aliases if a.strip()],
        "industry": str(profile.get("industry") or ""),
        "keywords": keywords_list(profile),
        "brief": str(profile.get("brief") or ""),
        "competitors": [c.strip() for c in competitors if c.strip()],
        "topics": [t.strip() for t in topics if t.strip()],
        "prompts_per_topic": n,
        "exclude_prompts": [p.strip() for p in exclude_prompts if p.strip()],
    }
    if taxonomy_lock is not None:
        payload["taxonomy_lock"] = taxonomy_lock.to_llm_payload()
    return payload


def _invoke_setup_prompts_llm(
    user_payload: dict[str, Any],
    *,
    on_live_call: Callable[[dict[str, Any]], None] | None = None,
) -> list[dict[str, Any]]:
    n = int(user_payload.get("prompts_per_topic") or PROMPT_PER_TOPIC)
    taxonomy_lock = user_payload.get("taxonomy_lock")
    lock_payload = taxonomy_lock if isinstance(taxonomy_lock, dict) else None
    messages = [
        {
            "role": "system",
            "content": setup_wizard_prompts_system(n=n, taxonomy_lock=lock_payload),
        },
        {
            "role": "user",
            "content": f"{SETUP_WIZARD_PROMPTS_USER_PREFIX}{json.dumps(user_payload, ensure_ascii=False, indent=2)}",
        },
    ]
    text, usage, latency_ms = chat_completion(messages, temperature=0.4, json_mode=True)
    if on_live_call is not None:
        on_live_call(usage)
    data = extract_json_object(text)
    rows = data.get("topics")
    if not isinstance(rows, list):
        raise ValueError("missing topics array")
    logger.debug("设置向导提示词 LLM: topics=%d %.0fms", len(rows), latency_ms)
    return [row for row in rows if isinstance(row, dict)]


def _rows_by_topic_name(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    by_name: dict[str, dict[str, Any]] = {}
    for row in rows:
        name = str(row.get("topic") or "").strip()
        if not name:
            continue
        key = topic_name_key(name)
        if key not in by_name:
            by_name[key] = row
    return by_name


def _prompts_from_row(
    row: dict[str, Any] | None,
    *,
    limit: int,
    excluded: set[str],
    taxonomy_lock: PromptTaxonomyLock | None = None,
) -> list[dict[str, str]]:
    if not row:
        return []
    raw_prompts = row.get("prompts")
    if not isinstance(raw_prompts, list):
        return []
    return _normalize_generated_prompts(
        raw_prompts,
        limit=limit,
        excluded=excluded,
        taxonomy_lock=taxonomy_lock,
    )


def _merge_prompt_lists(
    existing: list[dict[str, str]],
    extra: list[dict[str, str]],
    *,
    limit: int,
) -> list[dict[str, str]]:
    seen = {p["text"] for p in existing}
    out = list(existing)
    for item in extra:
        text = item["text"]
        if text in seen:
            continue
        seen.add(text)
        out.append(item)
        if len(out) >= limit:
            break
    return out


def _fill_prompt_gaps_from_plan(
    result: list[dict[str, Any]],
    *,
    profile: NicheProfile,
    plan: KeywordPlan,
    n: int,
    excluded: set[str],
    taxonomy_lock: PromptTaxonomyLock | None = None,
) -> None:
    """用已构建的 keyword_plan 补齐 LLM 未产满的主题，避免额外 LLM 重试。"""
    topics_needing_fill = [
        str(item["topic"])
        for item in result
        if len(item.get("prompts") or []) < n
    ]
    if not topics_needing_fill:
        return
    plan_items = build_prompts_from_plan(
        topics=topics_needing_fill,
        profile=profile,
        plan=plan,
        limit=n,
        excluded=excluded,
        taxonomy_lock=taxonomy_lock,
    )
    by_topic = {str(item["topic"]): item for item in plan_items}
    for item in result:
        topic = str(item["topic"])
        extra = by_topic.get(topic, {}).get("prompts") or []
        if not extra:
            continue
        item["prompts"] = _merge_prompt_lists(item.get("prompts") or [], extra, limit=n)


def _generate_setup_prompts_via_llm(
    *,
    entity: str,
    cleaned_topics: list[str],
    competitor_list: list[str],
    aliases: list[str] | None,
    profile: NicheProfile,
    plan: KeywordPlan,
    n: int,
    excluded: set[str],
    excluded_list: list[str],
    on_live_call: Callable[[str, dict[str, Any]], None] | None,
    taxonomy_lock: PromptTaxonomyLock | None = None,
) -> list[dict[str, Any]]:
    user_payload = _build_user_payload(
        entity=entity,
        topics=cleaned_topics,
        competitors=competitor_list,
        aliases=list(aliases or []),
        prompts_per_topic=n,
        exclude_prompts=excluded_list,
        profile=profile,
        taxonomy_lock=taxonomy_lock,
    )
    billing_key = hashlib.sha256(
        json.dumps(user_payload, ensure_ascii=False, sort_keys=True).encode()
    ).hexdigest()[:16]

    def _on_usage(usage: dict[str, Any]) -> None:
        if on_live_call is not None:
            on_live_call(f"batch:{billing_key}", usage)

    by_name = _rows_by_topic_name(
        _invoke_setup_prompts_llm(user_payload, on_live_call=_on_usage)
    )
    result: list[dict[str, Any]] = [
        {
            "topic": topic,
            "prompts": _prompts_from_row(
                by_name.get(topic_name_key(topic)),
                limit=n,
                excluded=excluded,
                taxonomy_lock=taxonomy_lock,
            ),
        }
        for topic in cleaned_topics
    ]

    _fill_prompt_gaps_from_plan(
        result,
        profile=profile,
        plan=plan,
        n=n,
        excluded=excluded,
        taxonomy_lock=taxonomy_lock,
    )

    empty = [str(item["topic"]) for item in result if not item["prompts"]]
    if empty:
        raise ValueError(f"以下监测主题未生成有效问句：{'、'.join(empty)}")

    validate_generated_prompts(result)

    short = [str(item["topic"]) for item in result if 0 < len(item["prompts"]) < n]
    if short:
        logger.warning(
            "设置向导提示词: 以下主题问句不足 %d 条: %s",
            n,
            "、".join(short),
        )

    logger.info(
        "设置向导提示词(LLM): entity=%r topics=%d prompts=%d",
        user_payload["entity"],
        len(result),
        sum(len(item["prompts"]) for item in result),
    )
    return result


def generate_setup_prompts(
    *,
    entity: str,
    topics: list[str],
    competitors: list[str] | None = None,
    aliases: list[str] | None = None,
    profile: NicheProfile,
    prompts_per_topic: int = PROMPT_PER_TOPIC,
    exclude_prompts: list[str] | None = None,
    on_live_call: Callable[[str, dict[str, Any]], None] | None = None,
    taxonomy_lock: PromptTaxonomyLock | None = None,
) -> list[dict[str, Any]]:
    """每主题至多 prompts_per_topic 条。

    LLM 解析/结构失败回退 keyword_plan。
    LLMProviderError（上游 API）不回退——调用方应感知真实失败，且计费已在成功响应后发生。
    """
    cleaned_topics = [t.strip() for t in topics if t.strip()]
    if not cleaned_topics:
        return []

    excluded_list = [p.strip() for p in (exclude_prompts or []) if p.strip()]
    excluded = set(excluded_list)
    n = max(1, min(int(prompts_per_topic), PROMPT_MAX_PER_TOPIC))
    competitor_list = [c.strip() for c in (competitors or []) if c.strip()]
    plan = build_keyword_plan(profile)

    try:
        return _generate_setup_prompts_via_llm(
            entity=entity,
            cleaned_topics=cleaned_topics,
            competitor_list=competitor_list,
            aliases=aliases,
            profile=profile,
            plan=plan,
            n=n,
            excluded=excluded,
            excluded_list=excluded_list,
            on_live_call=on_live_call,
            taxonomy_lock=taxonomy_lock,
        )
    except ValueError as exc:
        logger.info("设置向导提示词: LLM 未产出有效问句，回退 keyword_plan: %s", exc)
    except LLMProviderError:
        raise

    plan_result = build_prompts_from_plan(
        topics=cleaned_topics,
        profile=profile,
        plan=plan,
        limit=n,
        excluded=excluded,
        taxonomy_lock=taxonomy_lock,
    )
    empty_plan = [str(item["topic"]) for item in plan_result if not item["prompts"]]
    if empty_plan:
        raise ValueError(f"以下监测主题未生成有效问句：{'、'.join(empty_plan)}")

    validate_generated_prompts(plan_result)
    logger.info(
        "设置向导提示词(plan): entity=%r topics=%d prompts=%d",
        entity.strip() or "本品牌",
        len(plan_result),
        sum(len(item["prompts"]) for item in plan_result),
    )
    return plan_result
