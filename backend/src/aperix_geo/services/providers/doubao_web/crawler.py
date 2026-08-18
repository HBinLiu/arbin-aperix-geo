"""Doubao Web crawler entry: transport dispatch + concurrency (UI lives in ui_flow)."""

from __future__ import annotations

import logging
import threading
import time
from contextlib import contextmanager
from typing import Iterator

from aperix_geo.config import Settings, get_settings
from aperix_geo.services.providers.doubao_web.errors import DoubaoCrawlError
from aperix_geo.services.providers.doubao_web.runtime import (
    raise_from_job,
    resolve_crawl_transport,
    spawn_doubao_job,
)
from aperix_geo.services.providers.result import SamplingChatResult

logger = logging.getLogger(__name__)

_SEM_LOCK = threading.Lock()
_SEM: threading.Semaphore | None = None
_SEM_LIMIT = 0


def _crawl_semaphore(limit: int) -> threading.Semaphore:
    global _SEM, _SEM_LIMIT
    limit = max(1, int(limit))
    with _SEM_LOCK:
        if _SEM is None or _SEM_LIMIT != limit:
            _SEM = threading.Semaphore(limit)
            _SEM_LIMIT = limit
        return _SEM


@contextmanager
def concurrency_slot(settings: Settings) -> Iterator[None]:
    sem = _crawl_semaphore(settings.doubao_crawl_concurrency)
    if not sem.acquire(blocking=True, timeout=settings.doubao_crawl_timeout_s):
        raise DoubaoCrawlError("doubao crawl concurrency slot timeout")
    try:
        yield
    finally:
        sem.release()


def user_prompt_from_messages(messages: list[dict[str, str]]) -> str:
    for message in reversed(messages):
        if str(message.get("role") or "") == "user":
            text = str(message.get("content") or "").strip()
            if text:
                return text
    return ""


def crawl_doubao_chat(
    messages: list[dict[str, str]],
    *,
    settings: Settings | None = None,
    use_account_pool: bool = True,
) -> SamplingChatResult:
    """Run one Doubao Web sample. Raises DoubaoCrawlError subclasses on failure."""
    settings = settings or get_settings()
    if resolve_crawl_transport(settings) == "hybrid":
        from aperix_geo.services.providers.doubao_web.hybrid_crawl import (
            hybrid_crawl_doubao_chat,
        )

        return hybrid_crawl_doubao_chat(
            messages,
            settings=settings,
            use_account_pool=use_account_pool,
        )
    return _crawl_doubao_chat_ui(
        messages,
        settings=settings,
        use_account_pool=use_account_pool,
    )


def _crawl_doubao_chat_ui(
    messages: list[dict[str, str]],
    *,
    settings: Settings,
    use_account_pool: bool = True,
) -> SamplingChatResult:
    prompt = user_prompt_from_messages(messages)
    if not prompt:
        raise DoubaoCrawlError("empty user prompt")

    # Pool/SQLAlchemy stays out of geo-web-crawl image startup (lean import check).
    from aperix_geo.services.crawl_accounts.platforms import PLATFORM_DOUBAO
    from aperix_geo.services.providers.doubao_web.accounts import open_credential_session
    from aperix_geo.services.providers.doubao_web.jobs.crawl import build_crawl_payload

    session = open_credential_session(settings)
    started = time.monotonic()
    try:
        storage_state = session.acquire(use_account_pool=use_account_pool)
        payload = build_crawl_payload(
            prompt=prompt, storage_state=storage_state, settings=settings
        )
        payload["platform"] = PLATFORM_DOUBAO

        with concurrency_slot(settings):
            logger.info("doubao crawl transport=ui")
            job = spawn_doubao_job(
                payload,
                settings=settings,
                mode="crawl",
                timeout_s=float(settings.doubao_crawl_timeout_s),
            )

        if not job.get("ok"):
            session.handle_failed_job(job)
            raise_from_job(job)

        new_state = job.get("storage_state")
        session.release_ok(new_state if isinstance(new_state, dict) else None)
        return SamplingChatResult(
            text=str(job.get("text") or "").strip(),
            usage={},
            latency_ms=int(job.get("latency_ms") or (time.monotonic() - started) * 1000),
            source_urls=tuple(job.get("source_urls") or ()),
            web_search_mode="doubao_web_crawl",
            search_queries=tuple(job.get("search_queries") or ()),
            share_url=str(job.get("share_url") or ""),
        )
    finally:
        session.close()
