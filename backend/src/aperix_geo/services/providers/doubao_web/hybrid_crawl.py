"""Hybrid Doubao crawl: Web HTTP body/fanout + short UI share_url."""

from __future__ import annotations

import logging
import time
from typing import Any

from aperix_geo.config import Settings, get_settings
from aperix_geo.services.crawl_accounts.platforms import PLATFORM_DOUBAO
from aperix_geo.services.crawl_accounts.cookies import keep_session_storage_state
from aperix_geo.services.providers.doubao_web.accounts import open_credential_session
from aperix_geo.services.providers.doubao_web.crawler import user_prompt_from_messages
from aperix_geo.services.providers.doubao_web.errors import DoubaoCrawlError, DoubaoNeedsHumanOps
from aperix_geo.services.providers.doubao_web.jobs.share import build_share_payload
from aperix_geo.services.providers.doubao_web.runtime import (
    is_human_ops_job,
    raise_from_job,
    resolve_web_http_via,
    spawn_doubao_job,
)
from aperix_geo.services.providers.doubao_web.web_http.client import complete_web_http
from aperix_geo.services.providers.doubao_web.web_http.map_result import (
    map_web_http_to_sampling_result,
)
from aperix_geo.services.providers.result import SamplingChatResult

logger = logging.getLogger(__name__)


def hybrid_crawl_doubao_chat(
    messages: list[dict[str, str]],
    *,
    settings: Settings | None = None,
    use_account_pool: bool = True,
) -> SamplingChatResult:
    settings = settings or get_settings()
    prompt = user_prompt_from_messages(messages)
    if not prompt:
        raise DoubaoCrawlError("empty user prompt")

    session = open_credential_session(settings)
    started = time.monotonic()
    try:
        storage_state = session.acquire(use_account_pool=use_account_pool)
        account_fields = session.job_account_fields()
        # Profile jobs open Chrome on disk; do not ship the DB jar. httpx still needs it.
        browser_state = {"cookies": []} if account_fields else storage_state
        http_state = (
            storage_state if resolve_web_http_via(settings) == "httpx" else browser_state
        )

        try:
            logger.info("doubao crawl transport=hybrid step=http")
            http_job = complete_web_http(
                prompt=prompt,
                storage_state=http_state,
                settings=settings,
                extra=account_fields,
            )
        except DoubaoNeedsHumanOps as exc:
            session.request_human_ops(type(exc).__name__, str(exc))
            raise
        except DoubaoCrawlError as exc:
            session.release_fail(str(exc))
            raise

        exported = http_job.get("storage_state")
        if isinstance(exported, dict):
            storage_state = keep_session_storage_state(
                exported, fallback=storage_state, log_event="hybrid http"
            )

        share_payload = build_share_payload(
            storage_state=browser_state,
            settings=settings,
            conversation_id=str(http_job.get("conversation_id") or "").strip(),
        )
        share_payload["platform"] = PLATFORM_DOUBAO
        share_payload.update(account_fields)

        logger.info(
            "doubao crawl transport=hybrid step=share conversation_id=%s",
            share_payload.get("conversation_id") or "-",
        )
        share_job = spawn_doubao_job(share_payload, settings=settings, mode="share")

        if is_human_ops_job(share_job):
            session.handle_failed_job(share_job)
            raise_from_job(share_job)

        share_url = ""
        final_state: Any = None
        if share_job.get("ok"):
            share_url = str(share_job.get("share_url") or "").strip()
            final_state = share_job.get("storage_state")
        elif not share_job.get("ok"):
            logger.warning(
                "hybrid share skipped err=%s",
                share_job.get("error") or "share job failed",
            )

        session.release_ok(final_state if isinstance(final_state, dict) else storage_state)
        result = map_web_http_to_sampling_result(
            {
                "text": http_job.get("text"),
                "search_queries": http_job.get("search_queries"),
                "source_urls": http_job.get("source_urls"),
            },
            latency_ms=int((time.monotonic() - started) * 1000),
            share_url=share_url,
        )
        logger.info(
            "doubao crawl transport=hybrid ok text_len=%s share=%s queries=%s",
            len(result.text),
            bool(result.share_url),
            len(result.search_queries),
        )
        return result
    finally:
        session.close()
