"""Isolated Doubao browser crawl job (full UI: chat → panel → share)."""

from __future__ import annotations

import logging
import time
from typing import Any

from aperix_geo.config import Settings
from aperix_geo.services.crawl_accounts.cookies import (
    job_payload_storage_state,
    storage_state_from_context,
)
from aperix_geo.services.providers.doubao_web import selectors as sel
from aperix_geo.services.providers.doubao_web.errors import (
    DoubaoCrawlError,
    DoubaoNeedsHumanOps,
)
from aperix_geo.services.providers.doubao_web.extract import (
    clean_assistant_text,
    conversation_id_from_url,
    extract_quoted_queries,
    extract_urls,
    filter_http_urls,
    panel_present,
)
from aperix_geo.services.providers.doubao_web.runtime import (
    assert_no_captcha,
    job_error,
    job_ok,
    page_has_system_error,
    recover_system_error,
    wait_until_logged_in,
)

logger = logging.getLogger(__name__)

_CRAWL_SYSTEM_ERROR_ATTEMPTS = 2


def _crawl_failed_from_system_error(exc: BaseException, page: Any) -> bool:
    if "系统异常" in str(exc):
        return True
    try:
        return page_has_system_error(page)
    except Exception:
        return False


_EMPTY = {
    "text": "",
    "latency_ms": 0,
    "source_urls": [],
    "search_queries": [],
    "share_url": "",
}


def settings_from_crawl_payload(payload: dict[str, Any]) -> Settings:
    return Settings(
        doubao_crawl_timeout_s=float(payload.get("timeout_s") or 120),
        doubao_chat_base_url=str(payload.get("chat_base_url") or sel.CHAT_URL),
    )


def build_crawl_payload(
    *,
    prompt: str,
    storage_state: dict[str, Any],
    settings: Settings,
) -> dict[str, Any]:
    return {
        "mode": "crawl",
        "prompt": prompt,
        "storage_state": storage_state,
        "timeout_s": float(settings.doubao_crawl_timeout_s),
        "chat_base_url": (settings.doubao_chat_base_url or sel.CHAT_URL).strip() or sel.CHAT_URL,
    }


def run_doubao_browser_crawl_on_page(
    page: Any,
    context: Any,
    payload: dict[str, Any],
) -> dict[str, Any]:
    from aperix_geo.services.providers.doubao_web import ui_flow

    prompt = str(payload.get("prompt") or "").strip()
    storage_state = job_payload_storage_state(payload)
    if not prompt:
        return job_error(DoubaoCrawlError("empty user prompt"), **_EMPTY)
    if storage_state is None:
        return job_error(DoubaoCrawlError("storage_state missing"), **_EMPTY)

    settings = settings_from_crawl_payload(payload)
    timeout_ms = int(settings.doubao_crawl_timeout_s * 1000)
    started = time.monotonic()
    base_url = (settings.doubao_chat_base_url or sel.CHAT_URL).strip() or sel.CHAT_URL

    try:
        crawl_deadline = time.monotonic() + settings.doubao_crawl_timeout_s
        page.goto(base_url, wait_until="domcontentloaded", timeout=timeout_ms)
        wait_until_logged_in(page, base_url=base_url)
        assert_no_captcha(page)
        ui_flow.ensure_blank_chat(page, base_url=base_url)

        last_system_error: DoubaoCrawlError | None = None
        for attempt in range(1, _CRAWL_SYSTEM_ERROR_ATTEMPTS + 1):
            try:
                if attempt > 1:
                    logger.warning(
                        "doubao crawl retry after 系统异常 attempt=%s/%s url=%s",
                        attempt,
                        _CRAWL_SYSTEM_ERROR_ATTEMPTS,
                        page.url,
                    )
                    recover_system_error(page, base_url=base_url)
                    wait_until_logged_in(page, base_url=base_url)
                    assert_no_captcha(page)
                    ui_flow.ensure_blank_chat(page, base_url=base_url)

                prior_conv = conversation_id_from_url(page.url or "")
                ui_flow._fill_and_send(page, prompt, base_url=base_url)
                assert_no_captcha(page)
                # Fail fast if Doubao never created a thread / started generating.
                send_deadline = min(crawl_deadline, time.monotonic() + 25.0)
                ui_flow._wait_send_accepted(
                    page, prior_conv_id=prior_conv, deadline=send_deadline
                )
                assert_no_captcha(page)
                ui_flow._wait_generation_done(
                    page, settings=settings, deadline=crawl_deadline, user_prompt=prompt
                )
                assert_no_captcha(page)

                raw_text = ui_flow._extract_assistant_text(
                    page,
                    deadline=crawl_deadline,
                    user_prompt=prompt,
                )
                panel_text, panel_hrefs = ui_flow._extract_search_panel(page)
                queries = (
                    extract_quoted_queries(panel_text) if panel_present(panel_text) else ()
                )
                text = clean_assistant_text(
                    raw_text, user_prompt=prompt, search_queries=queries
                )
                if not text.strip():
                    raise DoubaoCrawlError(
                        "empty assistant reply; "
                        f"raw_len={len(raw_text or '')} {ui_flow._page_debug_summary(page)}"
                    )

                source_urls = filter_http_urls(
                    list(panel_hrefs) + list(extract_urls(panel_text))
                )

                logger.info("doubao crawl step=share url=%s", page.url)
                share_url = ui_flow.try_capture_share_url(page)
                logger.info("doubao crawl step=share done share=%s", bool(share_url))

                return job_ok(
                    text=text.strip(),
                    latency_ms=int((time.monotonic() - started) * 1000),
                    source_urls=list(source_urls),
                    search_queries=list(queries),
                    share_url=share_url,
                    storage_state=storage_state_from_context(
                        context, fallback=storage_state, log_event="crawl"
                    ),
                )
            except DoubaoCrawlError as exc:
                if (
                    attempt < _CRAWL_SYSTEM_ERROR_ATTEMPTS
                    and _crawl_failed_from_system_error(exc, page)
                ):
                    last_system_error = exc
                    continue
                raise

        if last_system_error is not None:
            raise last_system_error
        raise DoubaoCrawlError("doubao crawl exhausted without result")
    except DoubaoNeedsHumanOps as exc:
        return job_error(exc, **_EMPTY)
    except DoubaoCrawlError as exc:
        return job_error(exc, **_EMPTY)
    except Exception as exc:  # noqa: BLE001
        logger.exception("doubao browser crawl on_page unexpected error")
        return job_error(exc, **_EMPTY)
