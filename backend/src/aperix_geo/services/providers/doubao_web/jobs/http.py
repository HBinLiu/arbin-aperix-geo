"""Doubao Web HTTP job (mode=http): in-page fetch → SSE parse (BrowserOnly)."""

from __future__ import annotations

import json
import logging
import time
from typing import Any
from urllib.parse import urlencode

from aperix_geo.config import Settings
from aperix_geo.services.crawl_accounts.session_cookies import (
    storage_state_from_context,
    storage_state_has_session_cookies,
)
from aperix_geo.services.providers.doubao_web import selectors as sel
from aperix_geo.services.providers.doubao_web.errors import (
    DoubaoCrawlError,
    DoubaoLoginExpired,
    DoubaoNeedsHumanOps,
)
from aperix_geo.services.providers.doubao_web.runtime import (
    assert_no_captcha,
    job_error,
    job_ok,
    wait_until_logged_in,
)
from aperix_geo.services.providers.doubao_web.web_http.map_result import map_sse_events_to_fields
from aperix_geo.services.providers.doubao_web.web_http.protocol import (
    DEFAULT_BOT_ID,
    SAMANTHA_BASE_PARAMS,
    completion_body,
)

logger = logging.getLogger(__name__)

_EMPTY = {
    "text": "",
    "search_queries": [],
    "source_urls": [],
    "conversation_id": "",
    "latency_ms": 0,
}


def build_web_http_payload(
    *,
    prompt: str,
    storage_state: dict[str, Any],
    settings: Settings,
    conversation_id: str = "0",
) -> dict[str, Any]:
    return {
        "mode": "http",
        "prompt": prompt,
        "storage_state": storage_state,
        "timeout_s": float(settings.doubao_crawl_timeout_s),
        "chat_base_url": (settings.doubao_chat_base_url or sel.CHAT_URL).strip() or sel.CHAT_URL,
        "headless": bool(settings.doubao_crawl_headless),
        "conversation_id": (conversation_id or "0").strip() or "0",
        "bot_id": (settings.doubao_web_bot_id or DEFAULT_BOT_ID).strip() or DEFAULT_BOT_ID,
    }


def run_doubao_web_http_on_page(
    page: Any,
    context: Any,
    payload: dict[str, Any],
) -> dict[str, Any]:
    storage_state = payload.get("storage_state")
    prompt = str(payload.get("prompt") or "").strip()
    if not prompt:
        return job_error(DoubaoCrawlError("empty user prompt"), **_EMPTY)
    if not isinstance(storage_state, dict):
        return job_error(DoubaoCrawlError("storage_state missing"), **_EMPTY)
    if not storage_state_has_session_cookies(storage_state):
        return job_error(
            DoubaoLoginExpired("storage_state missing Doubao session cookies"),
            **_EMPTY,
        )

    base_url = str(payload.get("chat_base_url") or sel.CHAT_URL).strip() or sel.CHAT_URL
    timeout_s = float(payload.get("timeout_s") or 120)
    timeout_ms = min(180_000, int(timeout_s * 1000))
    conversation_id = str(payload.get("conversation_id") or "0").strip() or "0"
    bot_id = str(payload.get("bot_id") or DEFAULT_BOT_ID).strip() or DEFAULT_BOT_ID
    started = time.monotonic()

    try:
        page.goto(base_url, wait_until="domcontentloaded", timeout=timeout_ms)
        wait_until_logged_in(page)
        assert_no_captcha(page)
        page.wait_for_function(
            "() => typeof window.fetch === 'function'",
            timeout=min(30_000, timeout_ms),
        )
        page.wait_for_timeout(800)

        body_obj = completion_body(prompt, conversation_id=conversation_id, bot_id=bot_id)
        eval_timeout_ms = max(30_000, timeout_ms - 5_000)
        result = page.evaluate(
            """async ({ path, bodyJson, timeoutMs }) => {
                const ctrl = new AbortController();
                const timer = setTimeout(() => ctrl.abort(), timeoutMs);
                try {
                    const res = await fetch(path, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'Accept': '*/*',
                            'agw-js-conv': 'str, str',
                        },
                        body: bodyJson,
                        credentials: 'include',
                        signal: ctrl.signal,
                    });
                    const text = await res.text();
                    return { status: res.status, ok: res.ok, text };
                } catch (e) {
                    return { status: 0, ok: false, text: '', error: String(e) };
                } finally {
                    clearTimeout(timer);
                }
            }""",
            {
                "path": "/samantha/chat/completion?" + urlencode(SAMANTHA_BASE_PARAMS),
                "bodyJson": json.dumps(body_obj, ensure_ascii=False),
                "timeoutMs": eval_timeout_ms,
            },
        )

        if not isinstance(result, dict):
            raise DoubaoCrawlError(f"web_http evaluate returned unexpected: {result!r}")
        if result.get("error"):
            raise DoubaoCrawlError(f"web_http fetch error: {result['error']}")
        status = int(result.get("status") or 0)
        raw = str(result.get("text") or "")
        if status in (401, 403):
            raise DoubaoLoginExpired(f"web_http HTTP {status}")
        if status != 200:
            raise DoubaoCrawlError(f"web_http HTTP {status}: {raw[:400]}")
        if not raw.strip():
            raise DoubaoCrawlError(
                "web_http empty body (likely soft-block / captcha / bad cookie)"
            )

        fields = map_sse_events_to_fields(raw)
        text = (fields.get("text") or "").strip()
        if not text:
            raise DoubaoCrawlError("web_http parsed empty assistant text")

        return job_ok(
            text=text,
            search_queries=list(fields.get("search_queries") or []),
            source_urls=list(fields.get("source_urls") or []),
            conversation_id=str(fields.get("conversation_id") or conversation_id or ""),
            latency_ms=int((time.monotonic() - started) * 1000),
            storage_state=storage_state_from_context(
                context, fallback=storage_state, log_event="http"
            ),
        )
    except DoubaoNeedsHumanOps as exc:
        return job_error(exc, **_EMPTY)
    except DoubaoCrawlError as exc:
        return job_error(exc, **_EMPTY)
    except Exception as exc:  # noqa: BLE001
        logger.exception("doubao web_http job unexpected error")
        return job_error(exc, **_EMPTY)
