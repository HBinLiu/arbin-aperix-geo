"""Setup session 竞品列表：discover 写入候选，topics 覆盖为用户确认 enrich 结果。"""

from __future__ import annotations

import hashlib
import json
from typing import Any


def competitors_search_hash(
    *,
    subject_type: str,
    target: str,
    search_queries: list[str],
) -> str:
    """检索词未变时复用 discover 竞品搜索结果。"""
    payload = {
        "subject_type": subject_type,
        "target": target.strip(),
        "search_queries": sorted(q.strip() for q in search_queries if q.strip()),
    }
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def cached_competitors_result(
    session: dict[str, Any],
    *,
    competitors_hash: str,
) -> dict[str, Any] | None:
    if session.get("competitors_hash") != competitors_hash:
        return None
    competitors = session.get("competitors")
    if not isinstance(competitors, list) or not competitors:
        return None
    return {"competitors": competitors}


def session_patch_after_competitors(
    *,
    profile_dict: dict[str, Any],
    search_queries: list[str],
    competitors_hash: str,
    competitors: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "profile": profile_dict,
        "search_queries": search_queries,
        "competitors_hash": competitors_hash,
        "competitors": competitors,
        "profile_summary": "",
        "confirmed_competitors_hash": None,
        "monitoring_topics": [],
        "topic_clusters": [],
        "prompts_hash": None,
        "prompts_cache": None,
    }
