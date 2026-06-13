"""Setup Step2 竞品搜索结果 session 缓存。"""

from __future__ import annotations

import hashlib
import json
from typing import Any


def competitors_search_fingerprint(
    *,
    subject_type: str,
    target: str,
    micro_keywords: list[str],
) -> str:
    """检索词未变时复用 Step2 竞品搜索结果。"""
    payload = {
        "subject_type": subject_type,
        "target": target.strip(),
        "micro_keywords": sorted(k.strip() for k in micro_keywords if k.strip()),
    }
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def cached_competitors_result(
    session: dict[str, Any],
    *,
    fingerprint: str,
) -> dict[str, Any] | None:
    if session.get("competitors_fingerprint") != fingerprint:
        return None
    competitors = session.get("competitors_cache")
    profile_summary = str(session.get("profile_summary") or "").strip()
    if not isinstance(competitors, list) or not competitors or not profile_summary:
        return None
    return {
        "competitors": competitors,
        "profile_summary": profile_summary,
    }


def session_patch_after_competitors(
    *,
    profile_dict: dict[str, Any],
    keywords: list[str],
    confirmed_topics: list[str],
    profile_summary: str,
    fingerprint: str,
    competitors: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "profile": profile_dict,
        "micro_keywords": keywords,
        "monitoring_topics": confirmed_topics,
        "profile_summary": profile_summary,
        "competitors_fingerprint": fingerprint,
        "competitors_cache": competitors,
        "research_payload": None,
        "prompts_fingerprint": None,
        "prompts_cache": None,
    }
