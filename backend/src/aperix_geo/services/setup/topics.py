"""UI Step 1→2：用户确认竞品 → 监测主题 + profile_summary。"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from typing import Any

from uuid import UUID

from sqlalchemy.orm import Session

from aperix_geo.schemas.catalog import CompetitorItem
from aperix_geo.services.billing.quota import (
    assert_setup_ai_usage_available,
    charge_setup_ai_usage,
    usage_reference,
)
from aperix_geo.services.billing.usage_tokens import SETUP_LLM_PLATFORM
from aperix_geo.services.competitor.profile import profile_from_dict
from aperix_geo.services.setup.cache import get_session, update_session
from aperix_geo.services.competitor.enrich import enrich_confirmed_competitors
from aperix_geo.services.setup.helpers import require_deepseek_api_key, validate_confirmed_competitors
from aperix_geo.services.setup.llm.stages import (
    run_profile_summary_stage,
    run_topic_generation_stage,
)
from aperix_geo.services.setup.topic_items import cluster_topic_names, setup_topics_from_clusters

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
    db: Session,
    tenant_id: UUID,
    user_id: str,
    session_id: str,
    competitors: list[CompetitorItem],
) -> list[dict[str, str]]:
    """用户确认竞品后：补全竞品字段 → 监测主题 → profile_summary（均写入 session）。"""
    require_deepseek_api_key()
    t0 = time.perf_counter()

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

    logger.info(
        "设置向导·主题 开始 session=%s type=%s target=%r 竞品=%d",
        session_id[:8],
        subject_type,
        target,
        len(confirmed),
    )

    region = str(session.get("region") or "CN")
    language = str(session.get("language") or "zh-CN")
    profile = profile_from_dict(session.get("profile") or {})

    confirmed_hash = confirmed_competitors_hash(confirmed)
    competitors_changed = session.get("confirmed_competitors_hash") != confirmed_hash
    existing_clusters = session.get("topic_clusters")
    has_clusters = isinstance(existing_clusters, list) and len(existing_clusters) >= 1

    if has_clusters and not competitors_changed:
        topic_clusters = existing_clusters
    else:
        assert_setup_ai_usage_available(db, tenant_id)
        topic_clusters, usage = run_topic_generation_stage(
            profile=profile,
            subject_type=subject_type,
            entity_key=target,
            competitors=confirmed,
        )
        charge_setup_ai_usage(
            db,
            tenant_id=tenant_id,
            reference_id=usage_reference("monitoring_topics", session_id, confirmed_hash),
            platform=SETUP_LLM_PLATFORM,
            usage=usage,
        )
        db.commit()

    profile_summary = str(session.get("profile_summary") or "").strip()
    if competitors_changed or not profile_summary:
        assert_setup_ai_usage_available(db, tenant_id)
        profile_summary, usage = run_profile_summary_stage(
            profile=profile,
            subject_type=subject_type,
            target=target,
            region=region,
            language=language,
            entity_key=target,
            competitors=confirmed,
        )
        charge_setup_ai_usage(
            db,
            tenant_id=tenant_id,
            reference_id=usage_reference("profile_summary", session_id, confirmed_hash),
            platform=SETUP_LLM_PLATFORM,
            usage=usage,
        )
        db.commit()

    topic_names = cluster_topic_names(topic_clusters)
    patch: dict[str, Any] = {
        "confirmed_competitors_hash": confirmed_hash,
        "competitors": confirmed,
        "profile_summary": profile_summary,
        "monitoring_topics": topic_names,
        "topic_clusters": topic_clusters,
    }
    if competitors_changed or not has_clusters:
        patch["prompts_hash"] = None
        patch["prompts_cache"] = None

    if not update_session(
        user_id=user_id,
        session_id=session_id,
        patch=patch,
    ):
        raise ValueError("setup session not found")
    logger.info(
        "设置向导·主题 完成 session=%s 耗时=%.1fs 竞品=%d 主题=%d 摘要=%d字 重生成主题=%s",
        session_id[:8],
        time.perf_counter() - t0,
        len(confirmed),
        len(topic_names),
        len(profile_summary),
        competitors_changed or not has_clusters,
    )
    return setup_topics_from_clusters(topic_clusters)
