"""Setup UI Step 0→1 discover：竞品自动发现（不含 profile_summary）。"""

from __future__ import annotations

import logging
import time
from typing import Any
from uuid import UUID

from aperix_geo.services.competitor.discover import discover_competitors
from aperix_geo.services.competitor.profile import (
    keywords_list,
    merge_profile_updates,
    profile_from_dict,
    profile_to_dict,
)
from aperix_geo.services.setup.cache import (
    cached_competitors_result,
    competitors_search_hash,
    get_session,
    session_patch_after_competitors,
    update_session,
)

logger = logging.getLogger(__name__)


def discover_competitors_for_session(
    *,
    user_id: UUID,
    session_id: str,
    profile_dict: dict[str, Any] | None = None,
    keywords: list[str] | None = None,
) -> list[dict[str, Any]]:
    """搜索竞品并写入 session（profile_summary 留待用户确认竞品后生成）。"""
    session = get_session(user_id=str(user_id), session_id=session_id)
    if session is None:
        raise ValueError("setup session not found")

    base = profile_from_dict(profile_dict or session.get("profile") or {})
    confirmed = keywords if keywords is not None else (session.get("keywords") or [])
    profile = merge_profile_updates(
        base,
        keywords=confirmed if confirmed else None,
    )
    kw = keywords_list(profile)
    profile_dict = profile_to_dict(profile)

    subject_type = session["subject_type"]
    region = session.get("region", "CN")
    language = session.get("language", "zh-CN")
    target = session["target"]
    competitors_hash = competitors_search_hash(
        subject_type=subject_type,
        target=target,
        keywords=kw,
    )

    cached = cached_competitors_result(session, competitors_hash=competitors_hash)
    if cached is not None:
        update_session(
            user_id=str(user_id),
            session_id=session_id,
            patch=session_patch_after_competitors(
                profile_dict=profile_dict,
                keywords=kw,
                competitors_hash=competitors_hash,
                competitors=cached["competitors"],
            ),
        )
        logger.info(
            "设置向导·发现·竞品 缓存命中 session=%s 竞品=%d",
            session_id[:8],
            len(cached["competitors"]),
        )
        return cached["competitors"]

    logger.info("设置向导·发现·竞品 开始 session=%s type=%s target=%r", session_id[:8], subject_type, target)
    t0 = time.perf_counter()

    if subject_type == "domain":
        website_url = str(session.get("website_url") or "").strip()
        result = discover_competitors(
            profile,
            subject_type="domain",
            target=target,
            website_url=website_url,
            region=region,
            language=language,
        )
    else:
        result = discover_competitors(
            profile,
            subject_type="brand",
            target=target,
            region=region,
            language=language,
        )

    competitors = result.get("competitors") or []
    update_session(
        user_id=str(user_id),
        session_id=session_id,
        patch=session_patch_after_competitors(
            profile_dict=profile_dict,
            keywords=kw,
            competitors_hash=competitors_hash,
            competitors=competitors,
        ),
    )

    logger.info(
        "设置向导·发现·竞品 完成 session=%s 来源=%s 耗时=%.1fs 竞品=%d",
        session_id[:8],
        result.get("discovery_source", "unknown"),
        time.perf_counter() - t0,
        len(competitors),
    )
    return competitors
