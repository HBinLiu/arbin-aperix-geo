"""设置向导：初始提示词生成（LLM）。"""

from __future__ import annotations

import json
import logging
from typing import Any

from aperix_geo.services.providers.prompts import (
    SETUP_WIZARD_PROMPTS_USER_PREFIX,
    setup_wizard_prompts_system,
)
from aperix_geo.services.providers import chat_completion
from aperix_geo.services.prompts.taxonomy import normalize_funnel_stage, normalize_search_intent
from aperix_geo.utils.json import extract_json_object

logger = logging.getLogger(__name__)

PROMPT_PER_TOPIC = 10
PROMPT_MAX_PER_TOPIC = 20


def _exclude_set(exclude_prompts: list[str] | None) -> set[str]:
    return {p.strip() for p in (exclude_prompts or []) if p.strip()}


def _normalize_generated_prompts(
    raw: list[Any],
    *,
    limit: int,
    excluded: set[str] | None = None,
) -> list[dict[str, str]]:
    blocked = excluded or set()
    out: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in raw:
        if not isinstance(item, dict):
            continue
        text = str(item.get("text") or item.get("question") or "").strip()
        funnel_stage = normalize_funnel_stage(str(item.get("funnel") or item.get("funnel_stage") or ""))
        search_intent = normalize_search_intent(str(item.get("intent") or item.get("search_intent") or ""))
        if not text or text in seen or text in blocked:
            continue
        seen.add(text)
        out.append(
            {
                "text": text,
                "funnel_stage": funnel_stage,
                "search_intent": search_intent,
            }
        )
        if len(out) >= limit:
            break
    return out


def _build_user_payload(
    *,
    entity: str,
    topics: list[str],
    industry: str,
    features: str,
    customers: str,
    competitors: list[str],
    aliases: list[str],
    prompts_per_topic: int,
    exclude_prompts: list[str],
) -> dict[str, Any]:
    n = max(1, min(int(prompts_per_topic), PROMPT_MAX_PER_TOPIC))
    return {
        "entity": entity.strip() or "本品牌",
        "aliases": [a.strip() for a in aliases if a.strip()],
        "industry": industry,
        "features": features,
        "customers": customers,
        "competitors": [c.strip() for c in competitors if c.strip()],
        "topics": [t.strip() for t in topics if t.strip()],
        "prompts_per_topic": n,
        "exclude_prompts": [p.strip() for p in exclude_prompts if p.strip()],
    }


def _invoke_setup_prompts_llm(user_payload: dict[str, Any]) -> list[dict[str, Any]]:
    n = int(user_payload.get("prompts_per_topic") or PROMPT_PER_TOPIC)
    messages = [
        {"role": "system", "content": setup_wizard_prompts_system(n=n)},
        {
            "role": "user",
            "content": f"{SETUP_WIZARD_PROMPTS_USER_PREFIX}{json.dumps(user_payload, ensure_ascii=False, indent=2)}",
        },
    ]
    text, _, latency_ms = chat_completion(messages, temperature=0.4, json_mode=True)
    data = extract_json_object(text)
    rows = data.get("topics")
    if not isinstance(rows, list):
        raise ValueError("missing topics array")
    logger.debug(
        "设置向导提示词 LLM: topics=%d %.0fms",
        len(rows),
        latency_ms,
    )
    return [row for row in rows if isinstance(row, dict)]


def _rows_by_topic_name(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    by_name: dict[str, dict[str, Any]] = {}
    for row in rows:
        name = str(row.get("topic") or "").strip()
        if not name:
            continue
        key = name.casefold()
        if key not in by_name:
            by_name[key] = row
    return by_name


def _prompts_from_row(
    row: dict[str, Any] | None,
    *,
    limit: int,
    excluded: set[str],
) -> list[dict[str, str]]:
    if not row:
        return []
    raw_prompts = row.get("prompts")
    if not isinstance(raw_prompts, list):
        return []
    return _normalize_generated_prompts(raw_prompts, limit=limit, excluded=excluded)


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


def generate_setup_prompts(
    *,
    entity: str,
    topics: list[str],
    industry: str = "",
    features: str = "",
    customers: str = "",
    competitors: list[str] | None = None,
    aliases: list[str] | None = None,
    prompts_per_topic: int = PROMPT_PER_TOPIC,
    exclude_prompts: list[str] | None = None,
) -> list[dict[str, Any]]:
    """每个主题返回至多 prompts_per_topic 条 LLM 生成的提示词（含 funnel / intent）。"""
    cleaned_topics = [t.strip() for t in topics if t.strip()]
    if not cleaned_topics:
        return []

    excluded = _exclude_set(exclude_prompts)
    excluded_list = [p.strip() for p in (exclude_prompts or []) if p.strip()]
    n = max(1, min(int(prompts_per_topic), PROMPT_MAX_PER_TOPIC))
    competitor_list = [c.strip() for c in (competitors or []) if c.strip()]

    user_payload = _build_user_payload(
        entity=entity,
        topics=cleaned_topics,
        industry=industry,
        features=features,
        customers=customers,
        competitors=competitor_list,
        aliases=list(aliases or []),
        prompts_per_topic=n,
        exclude_prompts=excluded_list,
    )

    by_name = _rows_by_topic_name(_invoke_setup_prompts_llm(user_payload))
    result: list[dict[str, Any]] = []
    retry_topics: list[str] = []

    for topic in cleaned_topics:
        prompts = _prompts_from_row(by_name.get(topic.casefold()), limit=n, excluded=excluded)
        if not prompts:
            retry_topics.append(topic)
        result.append({"topic": topic, "prompts": prompts})

    for topic in retry_topics:
        current = next(item for item in result if item["topic"] == topic)
        retry_exclude = excluded_list + [p["text"] for p in current["prompts"]]
        retry_payload = _build_user_payload(
            entity=entity,
            topics=[topic],
            industry=industry,
            features=features,
            customers=customers,
            competitors=competitor_list,
            aliases=list(aliases or []),
            prompts_per_topic=n,
            exclude_prompts=retry_exclude,
        )
        retry_row = _rows_by_topic_name(_invoke_setup_prompts_llm(retry_payload)).get(topic.casefold())
        extra = _prompts_from_row(retry_row, limit=n, excluded=excluded)
        for item in result:
            if item["topic"] != topic:
                continue
            item["prompts"] = _merge_prompt_lists(item["prompts"], extra, limit=n)
            break

    short = [str(item["topic"]) for item in result if 0 < len(item["prompts"]) < n]
    if short:
        logger.warning(
            "设置向导提示词: 以下主题问句不足 %d 条: %s",
            n,
            "、".join(short),
        )

    empty = [str(item["topic"]) for item in result if not item["prompts"]]
    if empty:
        raise ValueError(f"以下监测主题未生成有效问句：{'、'.join(empty)}")

    logger.info(
        "设置向导提示词: entity=%r topics=%d prompts=%d",
        user_payload["entity"],
        len(result),
        sum(len(item["prompts"]) for item in result),
    )
    return result
