"""设置向导：初始提示词生成（LLM）。"""

from __future__ import annotations

import hashlib
import json
import logging
from collections.abc import Callable
from typing import Any

from aperix_geo.services.competitor.types import NicheProfile
from aperix_geo.services.providers.prompts import (
    SETUP_WIZARD_PROMPTS_USER_PREFIX,
    setup_wizard_prompts_system,
)
from aperix_geo.services.providers import chat_completion
from aperix_geo.services.prompts.taxonomy import (
    PromptTaxonomyLock,
    normalize_decision_type,
    normalize_funnel_stage,
    normalize_search_intent,
)
from aperix_geo.services.setup.keyword_plan import (
    build_keyword_plan,
    build_topic_keyword_map,
    keyword_plan_to_dict,
)
from aperix_geo.services.setup.prompt_seed import build_prompts_from_seeds
from aperix_geo.services.setup.prompt_qa import validate_generated_prompts
from aperix_geo.services.setup.topic_items import clusters_for_prompt_topics, topic_name_key
from aperix_geo.utils.json import extract_json_object

logger = logging.getLogger(__name__)

from aperix_geo.services.prompts.constants import PROMPT_MAX_PER_TOPIC, PROMPT_PER_TOPIC


def _exclude_set(exclude_prompts: list[str] | None) -> set[str]:
    return {p.strip() for p in (exclude_prompts or []) if p.strip()}


def _normalize_generated_prompts(
    raw: list[Any],
    *,
    limit: int,
    excluded: set[str] | None = None,
    taxonomy_lock: PromptTaxonomyLock | None = None,
) -> list[dict[str, str]]:
    blocked = excluded or set()
    out: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in raw:
        if not isinstance(item, dict):
            continue
        text = str(item.get("text") or "").strip()
        funnel_stage = normalize_funnel_stage(str(item.get("funnel") or ""))
        search_intent = normalize_search_intent(str(item.get("intent") or ""))
        decision_type = normalize_decision_type(str(item.get("decision") or ""))
        if not text or text in seen or text in blocked:
            continue
        seen.add(text)
        row = {
            "text": text,
            "funnel_stage": funnel_stage,
            "search_intent": search_intent,
            "decision_type": decision_type,
        }
        if taxonomy_lock is not None:
            row = taxonomy_lock.apply_prompt_row(row)
        out.append(row)
        if len(out) >= limit:
            break
    return out


def _build_user_payload(
    *,
    entity: str,
    topics: list[str],
    topic_clusters: list[dict[str, Any]] | None,
    industry: str,
    features: str,
    customers: str,
    competitors: list[str],
    aliases: list[str],
    prompts_per_topic: int,
    exclude_prompts: list[str],
    profile: NicheProfile,
    validation_feedback: list[str] | None = None,
    taxonomy_lock: PromptTaxonomyLock | None = None,
) -> dict[str, Any]:
    n = max(1, min(int(prompts_per_topic), PROMPT_MAX_PER_TOPIC))
    clusters = clusters_for_prompt_topics(topics, topic_clusters)
    plan = build_keyword_plan(profile)
    payload: dict[str, Any] = {
        "entity": entity.strip() or "本品牌",
        "aliases": [a.strip() for a in aliases if a.strip()],
        "industry": industry,
        "features": features,
        "customers": customers,
        "competitors": [c.strip() for c in competitors if c.strip()],
        "topic_clusters": clusters,
        "prompts_per_topic": n,
        "exclude_prompts": [p.strip() for p in exclude_prompts if p.strip()],
        "keyword_plan": keyword_plan_to_dict(plan),
        "topic_keyword_map": build_topic_keyword_map(topics, plan=plan),
    }
    if validation_feedback:
        payload["validation_feedback"] = [s.strip() for s in validation_feedback if s.strip()]
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


def _validate_prompt_batch(
    rows: list[dict[str, Any]],
    *,
    keyword_plan: Any,
    topic_clusters: list[dict[str, Any]] | None,
) -> None:
    try:
        validate_generated_prompts(
            rows,
            keyword_plan=keyword_plan,
            topic_clusters=topic_clusters,
        )
    except ValueError as exc:
        logger.warning("设置向导提示词校验未通过: %s", exc)
        raise


def _fill_prompt_gaps_from_seeds(
    result: list[dict[str, Any]],
    *,
    topic_clusters: list[dict[str, Any]] | None,
    profile: NicheProfile,
    n: int,
    excluded: set[str],
    taxonomy_lock: PromptTaxonomyLock | None = None,
) -> None:
    """用 profile 长尾候选补齐 LLM 未产满的主题，避免额外 LLM 重试。"""
    topics_needing_fill = [
        str(item["topic"])
        for item in result
        if 0 < len(item.get("prompts") or []) < n or not item.get("prompts")
    ]
    if not topics_needing_fill:
        return
    seed_items = build_prompts_from_seeds(
        topics=topics_needing_fill,
        topic_clusters=topic_clusters,
        profile=profile,
        limit=n,
        excluded=excluded,
        taxonomy_lock=taxonomy_lock,
    )
    by_topic = {str(item["topic"]): item for item in seed_items}
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
    topic_clusters: list[dict[str, Any]] | None,
    industry: str,
    features: str,
    customers: str,
    competitor_list: list[str],
    aliases: list[str] | None,
    profile: NicheProfile,
    n: int,
    excluded: set[str],
    excluded_list: list[str],
    on_live_call: Callable[[str, dict[str, Any]], None] | None,
    taxonomy_lock: PromptTaxonomyLock | None = None,
) -> list[dict[str, Any]]:
    user_payload = _build_user_payload(
        entity=entity,
        topics=cleaned_topics,
        topic_clusters=topic_clusters,
        industry=industry,
        features=features,
        customers=customers,
        competitors=competitor_list,
        aliases=list(aliases or []),
        prompts_per_topic=n,
        exclude_prompts=excluded_list,
        profile=profile,
        taxonomy_lock=taxonomy_lock,
    )
    keyword_plan = build_keyword_plan(profile)
    cluster_payload = clusters_for_prompt_topics(cleaned_topics, topic_clusters)

    billing_key = hashlib.sha256(
        json.dumps(user_payload, ensure_ascii=False, sort_keys=True).encode()
    ).hexdigest()[:16]

    def _bill(stage: str) -> Callable[[dict[str, Any]], None]:
        def _inner(usage: dict[str, Any]) -> None:
            if on_live_call is not None:
                on_live_call(stage, usage)

        return _inner

    by_name = _rows_by_topic_name(
        _invoke_setup_prompts_llm(user_payload, on_live_call=_bill(f"batch:{billing_key}"))
    )
    result: list[dict[str, Any]] = []
    for topic in cleaned_topics:
        prompts = _prompts_from_row(
            by_name.get(topic_name_key(topic)),
            limit=n,
            excluded=excluded,
            taxonomy_lock=taxonomy_lock,
        )
        result.append({"topic": topic, "prompts": prompts})

    _fill_prompt_gaps_from_seeds(
        result,
        topic_clusters=topic_clusters,
        profile=profile,
        n=n,
        excluded=excluded,
        taxonomy_lock=taxonomy_lock,
    )

    empty = [str(item["topic"]) for item in result if not item["prompts"]]
    if empty:
        raise ValueError(f"以下监测主题未生成有效问句：{'、'.join(empty)}")

    _validate_prompt_batch(result, keyword_plan=keyword_plan, topic_clusters=cluster_payload)

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
    topic_clusters: list[dict[str, Any]] | None = None,
    industry: str = "",
    features: str = "",
    customers: str = "",
    competitors: list[str] | None = None,
    aliases: list[str] | None = None,
    profile: NicheProfile,
    prompts_per_topic: int = PROMPT_PER_TOPIC,
    exclude_prompts: list[str] | None = None,
    on_live_call: Callable[[str, dict[str, Any]], None] | None = None,
    taxonomy_lock: PromptTaxonomyLock | None = None,
) -> list[dict[str, Any]]:
    """每个主题返回至多 prompts_per_topic 条提示词（LLM 优先，失败时回退 seed）。"""
    cleaned_topics = [t.strip() for t in topics if t.strip()]
    if not cleaned_topics:
        return []

    excluded = _exclude_set(exclude_prompts)
    excluded_list = [p.strip() for p in (exclude_prompts or []) if p.strip()]
    n = max(1, min(int(prompts_per_topic), PROMPT_MAX_PER_TOPIC))
    competitor_list = [c.strip() for c in (competitors or []) if c.strip()]

    try:
        return _generate_setup_prompts_via_llm(
            entity=entity,
            cleaned_topics=cleaned_topics,
            topic_clusters=topic_clusters,
            industry=industry,
            features=features,
            customers=customers,
            competitor_list=competitor_list,
            aliases=aliases,
            profile=profile,
            n=n,
            excluded=excluded,
            excluded_list=excluded_list,
            on_live_call=on_live_call,
            taxonomy_lock=taxonomy_lock,
        )
    except ValueError as exc:
        logger.info("设置向导提示词: LLM 未产出有效问句，回退 seed: %s", exc)

    keyword_plan = build_keyword_plan(profile)
    cluster_payload = clusters_for_prompt_topics(cleaned_topics, topic_clusters)
    seed_result = build_prompts_from_seeds(
        topics=cleaned_topics,
        topic_clusters=topic_clusters,
        profile=profile,
        limit=n,
        excluded=excluded,
        taxonomy_lock=taxonomy_lock,
    )
    empty_seed = [str(item["topic"]) for item in seed_result if not item["prompts"]]
    if empty_seed:
        raise ValueError(f"以下监测主题未生成有效问句：{'、'.join(empty_seed)}")

    _validate_prompt_batch(
        seed_result,
        keyword_plan=keyword_plan,
        topic_clusters=cluster_payload,
    )
    logger.info(
        "设置向导提示词(seed): entity=%r topics=%d prompts=%d",
        entity.strip() or "本品牌",
        len(seed_result),
        sum(len(item["prompts"]) for item in seed_result),
    )
    return seed_result
