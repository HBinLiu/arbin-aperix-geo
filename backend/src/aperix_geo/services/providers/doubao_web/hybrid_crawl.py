"""Hybrid Doubao crawl: Web HTTP body/fanout + short UI share_url."""

from __future__ import annotations

import logging
import time
from typing import Any

from aperix_geo.config import Settings, get_settings
from aperix_geo.services.providers.doubao_web.accounts import open_credential_session
from aperix_geo.services.providers.doubao_web.crawler import (
    concurrency_slot,
    user_prompt_from_messages,
)
from aperix_geo.services.providers.doubao_web.errors import DoubaoCrawlError, DoubaoShareError
from aperix_geo.services.providers.doubao_web.runtime import raise_from_job
from aperix_geo.services.providers.doubao_web.jobs.share import build_share_payload
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

    from aperix_geo.services.crawl_accounts.platforms import PLATFORM_DOUBAO
    from aperix_geo.services.geo_web_crawl.spawn import run_geo_web_crawl_spawn

    session = open_credential_session(settings)
    started = time.monotonic()
    try:
        storage_state = session.acquire(use_account_pool=use_account_pool)

        try:
            with concurrency_slot(settings):
                logger.info("doubao crawl transport=hybrid step=http")
                http_job = complete_web_http(
                    prompt=prompt, storage_state=storage_state, settings=settings
                )
        except DoubaoCrawlError as exc:
            from aperix_geo.services.providers.doubao_web.errors import DoubaoNeedsHumanOps

            if isinstance(exc, DoubaoNeedsHumanOps):
                session.request_human_ops(type(exc).__name__, str(exc))
            else:
                session.release_fail(str(exc))
            raise

        if isinstance(http_job.get("storage_state"), dict):
            storage_state = http_job["storage_state"]

        share_payload = build_share_payload(
            storage_state=storage_state,
            settings=settings,
            conversation_id=str(http_job.get("conversation_id") or "").strip(),
        )
        share_payload["platform"] = PLATFORM_DOUBAO

        with concurrency_slot(settings):
            logger.info(
                "doubao crawl transport=hybrid step=share conversation_id=%s",
                share_payload.get("conversation_id") or "-",
            )
            share_job = run_geo_web_crawl_spawn(
                share_payload,
                timeout_s=float(share_payload.get("timeout_s") or 60),
                docker_image=(settings.geo_web_crawl_docker_image or "").strip(),
                mode="share",
                base_url=(settings.geo_web_crawl_base_url or "").strip(),
                token=(settings.geo_web_crawl_token or "").strip(),
            )

        if not share_job.get("ok"):
            session.handle_failed_job(share_job)
            raise_from_job(share_job)

        share_url = str(share_job.get("share_url") or "").strip()
        if not share_url:
            session.release_fail("empty share_url")
            raise DoubaoShareError("share job returned empty share_url")

        final_state = share_job.get("storage_state")
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
