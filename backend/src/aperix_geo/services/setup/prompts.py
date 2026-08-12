"""UI Step 2→3：按 session 生成初始提示词。"""

from __future__ import annotations

import logging
import time
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from aperix_geo.services.billing.quota import (
    assert_setup_ai_usage_available,
    charge_setup_ai_usage,
    usage_reference,
)
from aperix_geo.services.billing.usage_tokens import SETUP_LLM_PLATFORM
from aperix_geo.services.prompts.context import prompt_context_from_session
from aperix_geo.services.prompts.setup import generate_setup_prompts
from aperix_geo.services.setup.cache.prompts import cached_prompts, prompts_generation_hash
from aperix_geo.services.setup.cache.session import get_session, update_session
from aperix_geo.services.setup.helpers import (
    competitor_labels_from_session,
    require_deepseek_api_key,
)
from aperix_geo.services.setup.topic_items import normalize_topic_names

logger = logging.getLogger(__name__)


def _require_topics(topics: list[str]) -> list[str]:
    confirmed = normalize_topic_names(topics)
    if not confirmed:
        raise ValueError("至少需要一个监测主题")
    return confirmed


def generate_setup_prompts_for_session(
    *,
    db: Session,
    tenant_id: UUID,
    user_id: str,
    session_id: str,
    topics: list[str],
    exclude_prompts: list[str] | None = None,
) -> list[dict[str, Any]]:
    """按 session 生成初始提示词；同时写入用户确认后的 monitoring_topics。"""
    require_deepseek_api_key()
    assert_setup_ai_usage_available(db, tenant_id)
    t0 = time.perf_counter()

    session = get_session(user_id=user_id, session_id=session_id)
    if session is None:
        raise ValueError("setup session not found")

    confirmed_topics = _require_topics(topics)
    ctx = prompt_context_from_session(
        session,
        topics=confirmed_topics,
        exclude_prompts=exclude_prompts,
        competitor_labels=competitor_labels_from_session(session),
    )
    logger.info(
        "设置向导·提示词 开始 session=%s target=%r 主题=%d",
        session_id[:8],
        ctx["entity"],
        len(ctx["confirmed_topics"]),
    )
    prompts_hash = prompts_generation_hash(
        entity=ctx["entity"],
        topics=ctx["confirmed_topics"],
        competitors=ctx["competitors"],
        industry=ctx["industry"],
        keywords=ctx["keywords"],
        brief=ctx["brief"],
        aliases=ctx["aliases"],
        exclude_prompts=ctx["excluded"],
    )

    cached = cached_prompts(session, prompts_hash=prompts_hash)
    if cached is not None:
        update_session(
            user_id=user_id,
            session_id=session_id,
            patch={"monitoring_topics": ctx["confirmed_topics"]},
        )
        logger.info(
            "设置向导·提示词 完成 session=%s 耗时=%.1fs 主题=%d 问句=%d 来源=缓存",
            session_id[:8],
            time.perf_counter() - t0,
            len(ctx["confirmed_topics"]),
            sum(len(row.get("prompts") or []) for row in cached),
        )
        return cached

    def _bill(stage: str, usage: dict) -> None:
        charge_setup_ai_usage(
            db,
            tenant_id=tenant_id,
            reference_id=usage_reference("setup_prompts", session_id, prompts_hash, stage),
            platform=SETUP_LLM_PLATFORM,
            usage=usage,
        )

    items = generate_setup_prompts(
        entity=ctx["entity"],
        topics=ctx["confirmed_topics"],
        competitors=ctx["competitors"],
        aliases=ctx["aliases"],
        exclude_prompts=ctx["excluded"],
        profile=ctx["profile"],
        on_live_call=_bill,
    )
    update_session(
        user_id=user_id,
        session_id=session_id,
        patch={
            "monitoring_topics": ctx["confirmed_topics"],
            "prompts_hash": prompts_hash,
            "prompts_cache": items,
        },
    )
    db.commit()
    logger.info(
        "设置向导·提示词 完成 session=%s 耗时=%.1fs 主题=%d 问句=%d 来源=生成",
        session_id[:8],
        time.perf_counter() - t0,
        len(ctx["confirmed_topics"]),
        sum(len(row.get("prompts") or []) for row in items),
    )
    return items
