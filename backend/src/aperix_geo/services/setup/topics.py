"""UI Step 竞品→主题：保存竞品 + 默认/用户主题 + 模板摘要（无主题 LLM）。"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from typing import Any

from uuid import UUID

from sqlalchemy.orm import Session

from aperix_geo.schemas.catalog import CompetitorItem
from aperix_geo.services.competitor.enrich import enrich_confirmed_competitors
from aperix_geo.services.competitor.profile import keywords_list, profile_from_dict
from aperix_geo.services.competitor.topic_types import MAX_MONITORING_TOPICS
from aperix_geo.services.setup.cache import get_session, update_session
from aperix_geo.services.setup.cache.discover import get_discover_job, wait_discover_job
from aperix_geo.services.setup.exceptions import MaterialsInsufficientError
from aperix_geo.services.setup.helpers import validate_confirmed_competitors
from aperix_geo.services.setup.llm.stages import run_profile_summary_stage
from aperix_geo.services.setup.materials import assert_niche_profile_sufficient
from aperix_geo.services.setup.topic_items import normalize_topic_names, setup_topics_from_names
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


def _resolve_monitoring_topics(session: dict[str, Any]) -> list[str]:
    """优先 session 已有主题；否则用画像 keywords。"""
    existing = session.get("monitoring_topics")
    if isinstance(existing, list) and existing:
        names = normalize_topic_names(existing)
        if names:
            return names

    profile = profile_from_dict(session.get("profile") or {})
    names = keywords_list(profile)[:MAX_MONITORING_TOPICS]
    if not names:
        raise ValueError("缺少监测主题：请先完成画像或手动填写主题")
    return names


def _session_has_usable_profile(session: dict[str, Any]) -> bool:
    try:
        assert_niche_profile_sufficient(profile_from_dict(session.get("profile") or {}))
    except MaterialsInsufficientError:
        return False
    return True


def _ensure_discover_profile(*, user_id: str, session_id: str) -> dict[str, Any]:
    """若画像未就绪则短等 Celery discover job。"""
    session = get_session(user_id=user_id, session_id=session_id)
    if session is None:
        raise ValueError("setup session not found")
    if _session_has_usable_profile(session):
        return session

    job = get_discover_job(user_id=user_id, session_id=session_id)
    if job and str(job.get("status") or "") == "failed":
        raise MaterialsInsufficientError(str(job.get("error") or "画像生成失败，请返回上一步重试"))

    if job and str(job.get("status") or "") in ("pending", "running"):
        logger.info("设置向导·主题 等待画像 session=%s", session_id[:8])
        finished = wait_discover_job(user_id=user_id, session_id=session_id, timeout_s=120.0)
        status = str(finished.get("status") or "")
        if status == "failed":
            raise MaterialsInsufficientError(str(finished.get("error") or "画像生成失败，请返回上一步重试"))
        if status != "ready":
            raise MaterialsInsufficientError("画像生成超时，请稍后重试")
        session = get_session(user_id=user_id, session_id=session_id)
        if session is None:
            raise ValueError("setup session not found")
        if not _session_has_usable_profile(session):
            raise MaterialsInsufficientError("画像尚未就绪，请稍后重试")
        return session

    # 无 job 且无画像：可能是旧会话或任务丢失
    raise MaterialsInsufficientError("画像尚未生成，请返回上一步重新开始分析")


def run_setup_topics_step(
    *,
    db: Session,
    tenant_id: UUID,
    user_id: str,
    session_id: str,
    competitors: list[CompetitorItem],
) -> list[dict[str, str]]:
    """用户确认竞品后：保存竞品、默认主题（keywords）、模板摘要。"""
    _ = (db, tenant_id)
    t0 = time.perf_counter()

    session = _ensure_discover_profile(user_id=user_id, session_id=session_id)

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

    topic_names = _resolve_monitoring_topics(session)

    profile_summary = str(session.get("profile_summary") or "").strip()
    if competitors_changed or not profile_summary:
        profile_summary, _usage = run_profile_summary_stage(
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
        "monitoring_topics": topic_names,
    }
    if competitors_changed:
        patch["prompts_hash"] = None
        patch["prompts_cache"] = None

    if not update_session(
        user_id=user_id,
        session_id=session_id,
        patch=patch,
    ):
        raise ValueError("setup session not found")
    logger.info(
        "设置向导·主题 完成 session=%s 耗时=%.1fs 竞品=%d 主题=%d 摘要=%d字",
        session_id[:8],
        time.perf_counter() - t0,
        len(confirmed),
        len(topic_names),
        len(profile_summary),
    )
    return setup_topics_from_names(topic_names)
