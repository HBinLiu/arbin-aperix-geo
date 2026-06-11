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

PROMPT_MAX_PER_TOPIC = 20
PROMPTS_PER_TOPIC = 10


def _normalize_generated_prompts(raw: list[Any], *, limit: int) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in raw:
        if isinstance(item, str):
            text = item.strip()
            funnel_stage = normalize_funnel_stage(None)
            search_intent = normalize_search_intent(None)
        elif isinstance(item, dict):
            text = str(item.get("text") or item.get("question") or "").strip()
            funnel_stage = normalize_funnel_stage(str(item.get("funnel") or item.get("funnel_stage") or ""))
            search_intent = normalize_search_intent(str(item.get("intent") or item.get("search_intent") or ""))
        else:
            continue
        if not text or text in seen:
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


def generate_setup_prompts(
    *,
    entity: str,
    topics: list[str],
    industry: str = "",
    core_features: str = "",
    target_customers: str = "",
    competitors: list[str] | None = None,
    aliases: list[str] | None = None,
    prompts_per_topic: int = PROMPTS_PER_TOPIC,
    exclude_prompts: list[str] | None = None,
) -> list[dict[str, Any]]:
    """每个主题返回至多 prompts_per_topic 条 LLM 生成的提示词（含 funnel / intent）。"""
    cleaned_topics = [t.strip() for t in topics if t.strip()]
    if not cleaned_topics:
        return []

    n = max(1, min(int(prompts_per_topic), PROMPT_MAX_PER_TOPIC))

    entity = entity.strip() or "本品牌"
    competitors = [c.strip() for c in (competitors or []) if c.strip()]
    alias_list = [a.strip() for a in (aliases or []) if a.strip()]
    excluded = [p.strip() for p in (exclude_prompts or []) if p.strip()][-60:]

    user_payload = {
        "entity": entity,
        "aliases": alias_list,
        "industry": industry,
        "core_features": core_features,
        "target_customers": target_customers,
        "competitors": competitors[:8],
        "topics": cleaned_topics,
        "prompts_per_topic": n,
        "exclude_prompts": excluded,
    }

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

    by_name = {
        str(row.get("topic") or "").strip(): row
        for row in rows
        if isinstance(row, dict) and str(row.get("topic") or "").strip()
    }
    result: list[dict[str, Any]] = []
    for topic in cleaned_topics:
        row = by_name.get(topic) or next(
            (by_name[k] for k in by_name if k in topic or topic in k),
            None,
        )
        raw_prompts = row.get("prompts") if isinstance(row, dict) else []
        prompts = _normalize_generated_prompts(raw_prompts if isinstance(raw_prompts, list) else [], limit=n)
        result.append({"topic": topic, "prompts": prompts})

    logger.info(
        "设置向导提示词: entity=%r topics=%d %.0fms",
        entity,
        len(result),
        latency_ms,
    )
    return result
