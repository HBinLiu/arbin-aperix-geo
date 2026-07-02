"""Setup discover 竞品层：读 session、查缓存、调 competitor.discover、写回 session。"""

from __future__ import annotations

import logging
import time
from typing import Any
from uuid import UUID

from aperix_geo.services.competitor.discover import discover_competitors
from aperix_geo.services.competitor.profile import (
    merge_profile_updates,
    profile_from_dict,
    profile_to_dict,
    search_queries_list,
)
from aperix_geo.services.setup.cache import (
    cached_competitors_result,
    competitors_search_hash,
    get_session,
    session_patch_after_competitors,
    update_session,
)

logger = logging.getLogger(__name__)


def competitors_for_api_response(competitors: list[dict[str, Any]]) -> list[dict[str, str]]:
    """API 响应仅含 Step1 UI 字段；完整数据在 session.competitors。"""
    return [
        {
            "domain": str(item.get("domain") or "").strip(),
            "website_url": str(item.get("website_url") or "").strip(),
            "brand": str(item.get("brand") or "").strip(),
        }
        for item in competitors
    ]


def _profile_for_discover(
    session: dict[str, Any],
    *,
    profile_dict: dict[str, Any] | None,
    search_queries: list[str] | None,
):
    base = profile_from_dict(profile_dict or session.get("profile") or {})
    if search_queries is None:
        return base
    return merge_profile_updates(base, search_queries=search_queries if search_queries else None)


def _persist_session_competitors(
    *,
    user_id: UUID,
    session_id: str,
    profile_dict: dict[str, Any],
    search_queries: list[str],
    competitors_hash: str,
    competitors: list[dict[str, Any]],
) -> None:
    update_session(
        user_id=str(user_id),
        session_id=session_id,
        patch=session_patch_after_competitors(
            profile_dict=profile_dict,
            search_queries=search_queries,
            competitors_hash=competitors_hash,
            competitors=competitors,
        ),
    )


def discover_competitors_for_session(
    *,
    user_id: UUID,
    session_id: str,
    profile_dict: dict[str, Any] | None = None,
    search_queries: list[str] | None = None,
) -> list[dict[str, Any]]:
    """搜索竞品并写入 session（profile_summary 留待用户确认竞品后生成）。"""
    session = get_session(user_id=str(user_id), session_id=session_id)
    if session is None:
        raise ValueError("setup session not found")

    profile = _profile_for_discover(
        session,
        profile_dict=profile_dict,
        search_queries=search_queries,
    )
    sq = search_queries_list(profile)
    profile_dict = profile_to_dict(profile)

    subject_type = str(session["subject_type"])
    target = str(session["target"])
    region = str(session.get("region") or "CN")
    language = str(session.get("language") or "zh-CN")
    competitors_hash = competitors_search_hash(
        subject_type=subject_type,
        target=target,
        search_queries=sq,
    )

    logger.info(
        "设置向导·发现·竞品 开始 session=%s type=%s target=%r",
        session_id[:8],
        subject_type,
        target,
    )
    t0 = time.perf_counter()

    cached = cached_competitors_result(session, competitors_hash=competitors_hash)
    if cached is not None:
        competitors = cached["competitors"]
        _persist_session_competitors(
            user_id=user_id,
            session_id=session_id,
            profile_dict=profile_dict,
            search_queries=sq,
            competitors_hash=competitors_hash,
            competitors=competitors,
        )
        logger.info(
            "设置向导·发现·竞品 完成 session=%s 来源=缓存 耗时=%.1fs 竞品=%d",
            session_id[:8],
            time.perf_counter() - t0,
            len(competitors),
        )
        return competitors

    result = discover_competitors(
        profile,
        subject_type=subject_type,  # type: ignore[arg-type]
        target=target,
        website_url=str(session.get("website_url") or "").strip() if subject_type == "domain" else "",
        region=region,
        language=language,
    )
    competitors = result.get("competitors") or []

    _persist_session_competitors(
        user_id=user_id,
        session_id=session_id,
        profile_dict=profile_dict,
        search_queries=sq,
        competitors_hash=competitors_hash,
        competitors=competitors,
    )
    logger.info(
        "设置向导·发现·竞品 完成 session=%s 来源=%s 耗时=%.1fs 竞品=%d",
        session_id[:8],
        result.get("discovery_source", "unknown"),
        time.perf_counter() - t0,
        len(competitors),
    )
    return competitors
