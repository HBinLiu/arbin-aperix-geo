"""Doubao Web Playwright crawler: new chat → reply → fanout panel → share_url."""

from __future__ import annotations

import logging
import re
import threading
import time
from contextlib import contextmanager
from typing import Any, Iterator

from aperix_geo.config import Settings, get_settings
from aperix_geo.services.providers._helpers import dedupe_urls
from aperix_geo.services.providers.doubao_web.accounts import (
    load_storage_state_from_file,
    resolve_storage_state_path,
    save_storage_state,
)
from aperix_geo.services.providers.doubao_web.errors import DoubaoCrawlError, DoubaoLoginExpired, DoubaoShareError
from aperix_geo.services.providers.doubao_web.extract import (
    extract_quoted_queries,
    extract_urls,
    panel_present,
    pick_share_url,
)
from aperix_geo.services.providers.doubao_web import selectors as sel
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
def _concurrency_slot(settings: Settings) -> Iterator[None]:
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
) -> SamplingChatResult:
    """Run one Doubao Web sample. Raises DoubaoCrawlError subclasses on failure."""
    settings = settings or get_settings()
    prompt = user_prompt_from_messages(messages)
    if not prompt:
        raise DoubaoCrawlError("empty user prompt")

    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise DoubaoCrawlError("playwright is not installed") from exc

    from aperix_geo.db.session import SessionLocal
    from aperix_geo.services.doubao_accounts.pool import (
        AccountLease,
        acquire_account,
        mark_need_relogin,
        release_account,
    )

    db = SessionLocal()
    lease: AccountLease | None = None
    storage_state: dict[str, Any] | None = None
    try:
        try:
            lease = acquire_account(db, settings=settings)
            if lease is not None:
                storage_state = lease.storage_state
                db.commit()
        except Exception:
            db.rollback()
            logger.warning("doubao account acquire failed; trying file cold-start", exc_info=True)
            lease = None

        if storage_state is None:
            storage_state = load_storage_state_from_file(settings)
        if storage_state is None:
            raise DoubaoCrawlError(
                "no Doubao credentials (pool empty / stale, or set DOUBAO_CRAWL_STORAGE_STATE_PATH)"
            )

        timeout_ms = int(settings.doubao_crawl_timeout_s * 1000)
        started = time.monotonic()
        base_url = (settings.doubao_chat_base_url or sel.CHAT_URL).strip() or sel.CHAT_URL

        with _concurrency_slot(settings):
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=bool(settings.doubao_crawl_headless))
                try:
                    context = browser.new_context(
                        storage_state=storage_state,
                        locale="zh-CN",
                        viewport={"width": 1440, "height": 900},
                    )
                    context.set_default_timeout(min(60_000, timeout_ms))
                    try:
                        context.grant_permissions(["clipboard-read", "clipboard-write"])
                    except Exception:
                        logger.debug("clipboard permission grant skipped", exc_info=True)

                    page = context.new_page()
                    page.goto(base_url, wait_until="domcontentloaded", timeout=timeout_ms)
                    _assert_logged_in(page)
                    _start_new_chat(page)
                    _assert_blank_composer(page)
                    _fill_and_send(page, prompt)
                    _wait_generation_done(page, timeout_ms=timeout_ms)

                    text = _extract_assistant_text(page)
                    if not text.strip():
                        raise DoubaoCrawlError("empty assistant reply")

                    panel_text = _extract_search_panel_text(page)
                    queries = extract_quoted_queries(panel_text) if panel_present(panel_text) else ()
                    source_urls = dedupe_urls(
                        list(extract_urls(panel_text)) + list(extract_urls(text))
                    )

                    share_url = ""
                    share_error: Exception | None = None
                    try:
                        share_url = _capture_share_url(page)
                    except Exception as exc:
                        share_error = exc

                    if settings.doubao_crawl_require_share_url and not share_url:
                        raise DoubaoShareError(
                            f"share_url required but missing: {share_error or 'empty'}"
                        ) from share_error

                    new_state = context.storage_state()
                    if lease is not None:
                        release_account(
                            db,
                            account_id=lease.account_id,
                            lease_owner=lease.lease_owner,
                            storage_state=new_state,
                            ok=True,
                        )
                        db.commit()
                        lease = None
                    else:
                        state_path = resolve_storage_state_path(settings)
                        if state_path is not None:
                            try:
                                save_storage_state(state_path, new_state)
                            except OSError:
                                logger.warning("failed to rewrite storage_state", exc_info=True)

                    latency_ms = int((time.monotonic() - started) * 1000)
                    return SamplingChatResult(
                        text=text.strip(),
                        usage={},
                        latency_ms=latency_ms,
                        source_urls=source_urls,
                        web_search_mode="doubao_web_crawl",
                        search_queries=queries,
                        share_url=share_url,
                    )
                except DoubaoLoginExpired:
                    if lease is not None:
                        mark_need_relogin(db, account_id=lease.account_id, error="login expired")
                        db.commit()
                        lease = None
                    raise
                except Exception as exc:
                    if lease is not None:
                        release_account(
                            db,
                            account_id=lease.account_id,
                            lease_owner=lease.lease_owner,
                            ok=False,
                            error=str(exc),
                        )
                        db.commit()
                        lease = None
                    raise
                finally:
                    browser.close()
    finally:
        if lease is not None:
            try:
                release_account(
                    db,
                    account_id=lease.account_id,
                    lease_owner=lease.lease_owner,
                    ok=False,
                    error="crawl aborted",
                )
                db.commit()
            except Exception:
                db.rollback()
                logger.warning("failed to release doubao account lease", exc_info=True)
        db.close()


def _assert_logged_in(page: Any) -> None:
    url = (page.url or "").lower()
    if "login" in url or "passport" in url:
        raise DoubaoLoginExpired(f"redirected to login: {page.url}")
    # Login CTA visible and composer missing ⇒ session dead.
    login_btn = page.get_by_role("button", name=sel.LOGIN_HINT)
    composer = _composer(page)
    if login_btn.count() > 0 and composer is None:
        raise DoubaoLoginExpired("login UI visible; storage_state expired")


def _start_new_chat(page: Any) -> None:
    btn = page.get_by_role("button", name=sel.NEW_CHAT_NAME)
    if btn.count() == 0:
        btn = page.get_by_text(sel.NEW_CHAT_NAME)
    if btn.count() > 0:
        try:
            btn.first.click(timeout=5_000)
            page.wait_for_timeout(800)
        except Exception:
            logger.debug("new chat click skipped", exc_info=True)
    # Prefer clean /chat/ URL without conversation id when possible.
    if re.search(r"/chat/[0-9a-fA-F-]{8,}", page.url or ""):
        try:
            page.goto(sel.CHAT_URL, wait_until="domcontentloaded")
            page.wait_for_timeout(500)
        except Exception:
            logger.debug("goto blank chat failed", exc_info=True)


def _assert_blank_composer(page: Any) -> None:
    """Soft check: conversation URL with many bubbles ⇒ likely old thread."""
    url = page.url or ""
    if not re.search(r"/chat/[0-9a-fA-F-]{8,}", url):
        return
    count = page.locator("[data-testid*='message'], div[class*='message-content']").count()
    if count > 4:
        raise DoubaoCrawlError(f"chat does not look blank (message-like nodes={count})")


def _composer(page: Any) -> Any | None:
    for css in sel.COMPOSER_SELECTORS:
        loc = page.locator(css)
        if loc.count() > 0:
            return loc.first
    role = page.get_by_role("textbox")
    if role.count() > 0:
        return role.last
    return None


def _fill_and_send(page: Any, prompt: str) -> None:
    box = _composer(page)
    if box is None:
        raise DoubaoCrawlError("chat composer not found")
    box.click()
    box.fill("")
    box.fill(prompt)
    send = page.get_by_role("button", name=sel.SEND_NAME)
    if send.count() > 0:
        send.last.click()
        return
    # Fallback: Enter
    box.press("Enter")


def _wait_generation_done(page: Any, *, timeout_ms: int) -> None:
    stop = page.get_by_role("button", name=sel.STOP_NAME)
    deadline = time.monotonic() + timeout_ms / 1000.0
    try:
        stop.first.wait_for(state="visible", timeout=min(30_000, timeout_ms))
    except Exception:
        # Fast replies may never show stop.
        page.wait_for_timeout(1_500)
        return

    remaining_ms = max(1_000, int((deadline - time.monotonic()) * 1000))
    try:
        stop.first.wait_for(state="hidden", timeout=remaining_ms)
    except Exception as exc:
        raise DoubaoCrawlError("generation did not finish before timeout") from exc
    page.wait_for_timeout(600)


def _extract_assistant_text(page: Any) -> str:
    for css in sel.ASSISTANT_MESSAGE_SELECTORS:
        loc = page.locator(css)
        if loc.count() > 0:
            text = (loc.last.inner_text(timeout=5_000) or "").strip()
            if text:
                return text

    # Fallback: largest text block that is not the user prompt echo.
    body = page.locator("main").inner_text(timeout=5_000) if page.locator("main").count() else page.inner_text("body")
    return (body or "").strip()


def _extract_search_panel_text(page: Any) -> str:
    hint = page.get_by_text(sel.SEARCH_PANEL_HINT)
    if hint.count() == 0:
        return ""
    try:
        # Expand if the header is a clickable summary.
        hint.last.click(timeout=2_000)
        page.wait_for_timeout(400)
    except Exception:
        pass
    # Prefer a nearby container; fall back to full page text for regex extract.
    try:
        container = hint.last.locator("xpath=ancestor::*[self::div or self::section][1]")
        text = (container.inner_text(timeout=3_000) or "").strip()
        if panel_present(text):
            # Walk up one more level for keyword + link lists.
            parent = hint.last.locator("xpath=ancestor::*[self::div or self::section][2]")
            wider = (parent.inner_text(timeout=3_000) or "").strip()
            return wider if len(wider) > len(text) else text
        return text
    except Exception:
        return page.inner_text("body") or ""


def _capture_share_url(page: Any) -> str:
    share = page.get_by_role("button", name=sel.SHARE_NAME)
    if share.count() == 0:
        share = page.get_by_text(sel.SHARE_NAME)
    if share.count() == 0:
        raise DoubaoShareError("share button not found")

    share.last.click()
    page.wait_for_timeout(500)

    # Prefer explicit copy-link control.
    copy_btn = page.get_by_role("button", name=sel.COPY_LINK_NAME)
    if copy_btn.count() == 0:
        copy_btn = page.get_by_text(sel.COPY_LINK_NAME)
    if copy_btn.count() > 0:
        try:
            copy_btn.first.click(timeout=3_000)
            page.wait_for_timeout(300)
        except Exception:
            logger.debug("copy link click failed", exc_info=True)

    candidates: list[str] = []

    # Clipboard (may fail in headless without permission).
    try:
        clip = page.evaluate("navigator.clipboard.readText()")
        if isinstance(clip, str) and clip.strip():
            candidates.append(clip.strip())
    except Exception:
        logger.debug("clipboard read failed", exc_info=True)

    # Dialog inputs / anchors.
    for loc in (
        page.locator("input[value^='http']"),
        page.locator("[role='dialog'] a[href^='http']"),
        page.locator("a[href*='doubao.com']"),
    ):
        try:
            n = min(loc.count(), 8)
            for i in range(n):
                el = loc.nth(i)
                for raw in (el.get_attribute("href"), el.get_attribute("value")):
                    if raw and str(raw).strip().startswith("http"):
                        candidates.append(str(raw).strip())
        except Exception:
            continue

    # Dialog plain text URLs.
    try:
        dialog = page.locator("[role='dialog']")
        if dialog.count() > 0:
            candidates.extend(extract_urls(dialog.last.inner_text(timeout=2_000) or ""))
    except Exception:
        pass

    url = pick_share_url(candidates)
    if not url:
        raise DoubaoShareError("could not read share URL from dialog/clipboard")
    return url
