"""UI Step 1→2：用户确认竞品 → 监测主题 + profile_summary。"""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

from aperix_geo.schemas.catalog import CompetitorItem
from aperix_geo.services.competitor.profile import profile_from_dict
from aperix_geo.services.setup.cache import get_session, update_session
from aperix_geo.services.competitor.enrich import enrich_confirmed_competitors
from aperix_geo.services.setup.helpers import require_deepseek_api_key, validate_confirmed_competitors
from aperix_geo.services.setup.llm.stages import (
    run_monitoring_topics_stage,
    run_profile_summary_stage,
)

logger = logging.getLogger(__name__)


def confirmed_competitors_hash(competitors: list[dict[str, Any]]) -> str:
    rows = []
    for item in competitors:
        aliases = item.get("aliases")
        alias_list: list[str] = []
        if isinstance(aliases, list):
            alias_list = sorted(str(a).strip().casefold() for a in aliases if str(a).strip())
        rows.append(
            {
                "domain": str(item.get("domain") or "").strip().casefold(),
                "brand": str(item.get("brand") or "").strip().casefold(),
                "website_url": str(item.get("website_url") or "").strip(),
                "summary": str(item.get("summary") or "").strip(),
                "aliases": alias_list,
            }
        )
    rows.sort(key=lambda r: (r["domain"], r["brand"], r["website_url"]))
    raw = json.dumps(rows, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _competitors_to_dicts(competitors: list[CompetitorItem]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for item in competitors:
        domain = item.domain.strip()
        brand = item.brand.strip()
        if not domain and not brand:
            continue
        row: dict[str, Any] = {
            "domain": domain,
            "website_url": item.website_url.strip(),
            "brand": brand,
            "summary": item.summary.strip(),
        }
        if item.aliases:
            row["aliases"] = list(item.aliases)
        out.append(row)
    return out


def run_setup_topics_step(
    *,
    user_id: str,
    session_id: str,
    competitors: list[CompetitorItem],
) -> list[str]:
    """用户确认竞品后：补全竞品字段 → 监测主题 → profile_summary（均写入 session）。"""
    require_deepseek_api_key()

    session = get_session(user_id=user_id, session_id=session_id)
    if session is None:
        raise ValueError("setup session not found")

    confirmed = enrich_confirmed_competitors(
        _competitors_to_dicts(competitors),
        session=session,
    )
    subject_type = str(session.get("subject_type") or "")
    validate_confirmed_competitors(subject_type=subject_type, competitors=confirmed)

    target = str(session.get("target") or "").strip()
    if not target:
        raise ValueError("setup session missing target")

    region = str(session.get("region") or "CN")
    language = str(session.get("language") or "zh-CN")
    profile = profile_from_dict(session.get("profile") or {})

    confirmed_hash = confirmed_competitors_hash(confirmed)
    competitors_changed = session.get("confirmed_competitors_hash") != confirmed_hash
    existing_topics = [
        str(t).strip()
        for t in (session.get("monitoring_topics") or [])
        if str(t).strip()
    ]

    if existing_topics and not competitors_changed:
        topics = existing_topics
    else:
        topics = run_monitoring_topics_stage(
            profile=profile,
            subject_type=subject_type,
            entity_key=target,
        )

    profile_summary = str(session.get("profile_summary") or "").strip()
    if competitors_changed or not profile_summary:
        profile_summary = run_profile_summary_stage(
            profile=profile,
            subject_type=subject_type,
            target=target,
            region=region,
            language=language,
            entity_key=target,
            competitors=confirmed,
        )

    patch: dict[str, Any] = {
        "confirmed_competitors_hash": confirmed_hash,
        "competitors": confirmed,
        "profile_summary": profile_summary,
        "monitoring_topics": topics,
        "research_payload": None,
    }
    if competitors_changed or not existing_topics:
        patch["prompts_hash"] = None
        patch["prompts_cache"] = None

    if not update_session(
        user_id=user_id,
        session_id=session_id,
        patch=patch,
    ):
        raise ValueError("setup session not found")
    logger.info(
        "设置向导·主题 完成 session=%s 竞品=%d 主题=%d 摘要=%d字 重生成主题=%s 已写入 session.competitors",
        session_id[:8],
        len(confirmed),
        len(topics),
        len(profile_summary),
        competitors_changed or not existing_topics,
    )
    return topics
