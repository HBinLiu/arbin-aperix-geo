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
from aperix_geo.services.providers.doubao_web.errors import (
    DoubaoCaptchaRequired,
    DoubaoCrawlError,
    DoubaoLoginExpired,
    DoubaoNeedsHumanOps,
    DoubaoShareError,
)
from aperix_geo.services.providers.doubao_web.extract import (
    blank_chat_failure_reason,
    clean_assistant_text,
    conversation_id_from_url,
    extract_quoted_queries,
    extract_urls,
    filter_http_urls,
    page_looks_like_captcha,
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

    from aperix_geo.services.providers.doubao_web.browser import browser_page_session
    from aperix_geo.db.session import SessionLocal
    from aperix_geo.services.doubao_accounts.human_ops import request_human_intervention
    from aperix_geo.services.doubao_accounts.pool import (
        AccountLease,
        acquire_account,
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
            with browser_page_session(settings, storage_state=storage_state) as (page, context):
                try:
                    crawl_deadline = time.monotonic() + settings.doubao_crawl_timeout_s
                    page.goto(base_url, wait_until="domcontentloaded", timeout=timeout_ms)
                    _assert_logged_in(page)
                    _assert_no_captcha(page)
                    _ensure_blank_chat(page, base_url=base_url)
                    _fill_and_send(page, prompt)
                    _assert_no_captcha(page)
                    _wait_generation_done(
                        page,
                        settings=settings,
                        deadline=crawl_deadline,
                    )
                    _assert_no_captcha(page)

                    # Extract answer BEFORE expanding the search panel (panel text pollutes DOM).
                    raw_text = _extract_assistant_text(page)
                    panel_text, panel_hrefs = _extract_search_panel(page)
                    queries = extract_quoted_queries(panel_text) if panel_present(panel_text) else ()
                    text = clean_assistant_text(
                        raw_text,
                        user_prompt=prompt,
                        search_queries=queries,
                    )
                    if not text.strip():
                        raise DoubaoCrawlError("empty assistant reply")

                    # Panel DOM is the source of truth for citations (no host allow/deny lists).
                    source_urls = filter_http_urls(
                        list(panel_hrefs) + list(extract_urls(panel_text))
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
                except DoubaoNeedsHumanOps as exc:
                    # Login expired + captcha: same ticket + alert recovery.
                    if lease is not None:
                        reason = "captcha" if isinstance(exc, DoubaoCaptchaRequired) else "login_expired"
                        request_human_intervention(
                            db,
                            account_id=lease.account_id,
                            reason=reason,
                            error=str(exc),
                            settings=settings,
                        )
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


def _ensure_blank_chat(page: Any, *, base_url: str, attempts: int = 2) -> None:
    """Open a blank session and hard-validate before sending the sample prompt.

    Retries once on failure (goto landing + 新对话). Still dirty → DoubaoCrawlError
    so crawl_first can API-fallback instead of sampling into an old thread.
    """
    prior_id = conversation_id_from_url(page.url or "")
    last_reason = ""
    for attempt in range(1, max(1, attempts) + 1):
        _open_fresh_chat(page, base_url=base_url)
        page.wait_for_timeout(500)
        last_reason = _probe_blank_chat_reason(page, prior_conversation_id=prior_id)
        if not last_reason:
            logger.info(
                "blank chat ready attempt=%s url=%s prior_id=%s",
                attempt,
                page.url,
                prior_id or "-",
            )
            return
        logger.warning(
            "blank chat check failed attempt=%s/%s: %s url=%s",
            attempt,
            attempts,
            last_reason,
            page.url,
        )
    raise DoubaoCrawlError(
        f"failed to open blank chat after {attempts} attempts: {last_reason}"
    )


def _open_fresh_chat(page: Any, *, base_url: str) -> None:
    """Navigate to chat landing and click 新对话 when available."""
    target = (base_url or sel.CHAT_URL).strip() or sel.CHAT_URL
    try:
        page.goto(target, wait_until="domcontentloaded")
        page.wait_for_timeout(400)
    except Exception:
        logger.debug("goto chat landing failed", exc_info=True)

    btn = page.get_by_role("button", name=sel.NEW_CHAT_NAME)
    if btn.count() == 0:
        btn = page.get_by_text(sel.NEW_CHAT_NAME)
    if btn.count() > 0:
        try:
            btn.first.click(timeout=5_000)
            page.wait_for_timeout(600)
        except Exception:
            logger.debug("new chat click skipped", exc_info=True)

    # If still on a concrete thread URL, force landing again (stronger than click alone).
    if conversation_id_from_url(page.url or ""):
        try:
            page.goto(target, wait_until="domcontentloaded")
            page.wait_for_timeout(400)
        except Exception:
            logger.debug("second goto blank chat failed", exc_info=True)


def _probe_blank_chat_reason(page: Any, *, prior_conversation_id: str) -> str:
    """Collect DOM/URL signals and return blank_chat_failure_reason ('' if OK)."""
    md_texts: list[str] = []
    try:
        boxes = page.locator(".md-box-root")
        n = min(boxes.count(), 8)
        for i in range(n):
            try:
                md_texts.append(boxes.nth(i).inner_text(timeout=800) or "")
            except Exception:
                continue
    except Exception:
        pass

    message_like = 0
    try:
        message_like = page.locator(
            "[data-testid*='message'], div[class*='message-content']"
        ).count()
    except Exception:
        message_like = 0

    search_panel_hint = False
    try:
        body = page.locator("body").inner_text(timeout=1_500) or ""
        search_panel_hint = bool(sel.SEARCH_PANEL_HINT.search(body))
    except Exception:
        search_panel_hint = False

    return blank_chat_failure_reason(
        url=page.url or "",
        md_box_texts=md_texts,
        message_like_count=message_like,
        search_panel_hint=search_panel_hint,
        prior_conversation_id=prior_conversation_id,
    )


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


def _page_has_captcha(page: Any) -> bool:
    """Detect Doubao behavior captcha / 人机验证 overlays."""
    try:
        body = page.locator("body").inner_text(timeout=2_000) or ""
    except Exception:
        body = ""
    if page_looks_like_captcha(body):
        return True
    for css in sel.CAPTCHA_DOM_SELECTORS:
        try:
            loc = page.locator(css)
            n = min(loc.count(), 5)
            for i in range(n):
                if loc.nth(i).is_visible():
                    return True
        except Exception:
            continue
    return False


def _assert_no_captcha(page: Any) -> None:
    """Captcha uses the same human ticket/alert path as login expiry — never wait/auto-solve."""
    if _page_has_captcha(page):
        raise DoubaoCaptchaRequired(
            "behavior captcha detected; account needs human ticket/alert recovery "
            "(no auto-solve; sampling may API-fallback)"
        )


def _wait_generation_done(page: Any, *, settings: Settings, deadline: float) -> None:
    """Wait until streaming finishes: stop button gone and md-box data-streaming=false."""
    stop = page.get_by_role("button", name=sel.STOP_NAME)

    saw_stop = False
    poll_until = min(deadline, time.monotonic() + 30.0)
    while time.monotonic() < poll_until:
        _assert_no_captcha(page)
        try:
            if stop.count() > 0 and stop.first.is_visible():
                saw_stop = True
                break
        except Exception:
            pass
        try:
            box = page.locator(".md-box-root").last
            if box.count() > 0:
                flag = box.get_attribute("data-streaming")
                text = (box.inner_text(timeout=500) or "").strip()
                if text and flag != "true":
                    break
        except Exception:
            pass
        page.wait_for_timeout(500)

    if saw_stop:
        while time.monotonic() < deadline:
            _assert_no_captcha(page)
            try:
                if stop.count() == 0 or not stop.first.is_visible():
                    break
            except Exception:
                break
            page.wait_for_timeout(500)
        else:
            raise DoubaoCrawlError("generation did not finish before timeout (stop button)")

    _wait_md_box_streaming_false(page, settings=settings, deadline=deadline)
    page.wait_for_timeout(400)


def _wait_md_box_streaming_false(page: Any, *, settings: Settings, deadline: float) -> None:
    """Prefer last .md-box-root reaching data-streaming=false (Doubao stream end signal)."""
    remaining_ms = max(500, int((deadline - time.monotonic()) * 1000))
    box = page.locator(".md-box-root").last
    try:
        box.wait_for(state="attached", timeout=min(15_000, remaining_ms))
    except Exception:
        page.wait_for_timeout(1_500)
        return

    while time.monotonic() < deadline:
        _assert_no_captcha(page)
        try:
            flag = box.get_attribute("data-streaming")
            text = (box.inner_text(timeout=800) or "").strip()
            if text and flag != "true":
                return
        except Exception:
            pass
        page.wait_for_timeout(500)

    flag = ""
    try:
        flag = str(box.get_attribute("data-streaming") or "")
    except Exception:
        pass
    if flag == "true":
        raise DoubaoCrawlError("generation did not finish before timeout (data-streaming still true)")
    page.wait_for_timeout(800)


def _extract_assistant_text(page: Any) -> str:
    """Prefer Doubao ``md-box-root`` HTML → Markdown; fan-out panel is outside this node."""
    from aperix_geo.services.providers.doubao_web.extract import md_box_html_to_markdown

    for css in sel.MD_BOX_SELECTORS:
        loc = page.locator(css)
        try:
            n = loc.count()
        except Exception:
            continue
        if n <= 0:
            continue
        # Last streamed box is the current assistant reply.
        target = loc.last
        try:
            html = target.evaluate("el => el.outerHTML")
        except Exception:
            html = ""
        if isinstance(html, str) and html.strip():
            md = md_box_html_to_markdown(html)
            if md.strip():
                return md
        try:
            plain = (target.inner_text(timeout=5_000) or "").strip()
        except Exception:
            plain = ""
        if plain:
            return plain

    # Fallback: legacy message containers (no md-box on older shells).
    for css in sel.ASSISTANT_MESSAGE_SELECTORS:
        loc = page.locator(css)
        try:
            n = loc.count()
        except Exception:
            continue
        if n <= 0:
            continue
        try:
            text = (loc.last.inner_text(timeout=5_000) or "").strip()
        except Exception:
            continue
        if text:
            return text
    return (page.inner_text("body") or "").strip()


def _panel_root(hint: Any) -> Any:
    """Walk up from the「搜索 N 个关键词」header to a container that holds references."""
    best = hint
    best_text = ""
    for depth in range(1, 8):
        try:
            node = hint.locator(f"xpath=ancestor::*[self::div or self::section or self::aside][{depth}]")
            if node.count() == 0:
                break
            text = (node.first.inner_text(timeout=2_000) or "").strip()
        except Exception:
            break
        if not text:
            continue
        if panel_present(text) and ("http" in text.lower() or "参考" in text or "资料" in text):
            best = node.first
            best_text = text
            continue
        if best_text and len(text) > len(best_text) * 3:
            break
        if len(text) > len(best_text):
            best = node.first
            best_text = text
    return best


def _extract_search_panel(page: Any) -> tuple[str, tuple[str, ...]]:
    """Return (panel_text, hrefs from panel anchors)."""
    hint = page.get_by_text(sel.SEARCH_PANEL_HINT)
    if hint.count() == 0:
        return "", ()
    target = hint.last
    try:
        target.click(timeout=2_000)
        page.wait_for_timeout(500)
    except Exception:
        pass

    # Some builds put keywords / references behind tabs inside the panel.
    for tab_name in (r"参考资料", r"资料", r"来源", r"搜索关键词", r"关键词"):
        try:
            tab = page.get_by_text(re.compile(tab_name))
            found = None
            for i in range(min(tab.count(), 6)):
                el = tab.nth(i)
                try:
                    if el.is_visible():
                        found = el
                        break
                except Exception:
                    continue
            if found is not None:
                found.click(timeout=2_000)
                page.wait_for_timeout(400)
        except Exception:
            continue

    try:
        root = _panel_root(target)
        text = (root.inner_text(timeout=3_000) or "").strip()
    except Exception:
        text = page.inner_text("body") or ""
        root = page.locator("body")

    hrefs: list[str] = []
    try:
        anchors = root.locator("a[href]")
        n = min(anchors.count(), 80)
        for i in range(n):
            el = anchors.nth(i)
            try:
                href = (el.get_attribute("href") or "").strip()
            except Exception:
                continue
            if href.startswith("//"):
                href = "https:" + href
            if href.startswith("http"):
                hrefs.append(href)
            for attr in ("data-url", "data-href", "data-src", "data-link"):
                try:
                    raw = (el.get_attribute(attr) or "").strip()
                except Exception:
                    raw = ""
                if raw.startswith("http"):
                    hrefs.append(raw)
    except Exception:
        logger.debug("panel href scrape failed", exc_info=True)

    try:
        links = root.get_by_role("link")
        n = min(links.count(), 80)
        for i in range(n):
            el = links.nth(i)
            try:
                href = (el.get_attribute("href") or "").strip()
            except Exception:
                continue
            if href.startswith("//"):
                href = "https:" + href
            if href.startswith("http"):
                hrefs.append(href)
    except Exception:
        pass

    return text, dedupe_urls(hrefs)


def _first_visible(locator: Any, *, limit: int = 12) -> Any | None:
    try:
        n = min(int(locator.count()), limit)
    except Exception:
        return None
    for i in range(n):
        el = locator.nth(i)
        try:
            if el.is_visible():
                return el
        except Exception:
            continue
    return None


def _dismiss_overlay(page: Any) -> None:
    try:
        page.keyboard.press("Escape")
        page.wait_for_timeout(200)
    except Exception:
        pass


def _share_menu_open(page: Any) -> bool:
    """True when the conversation overflow menu (with 分享) looks open."""
    return _locate_share_control(page) is not None


def _locate_share_control(page: Any) -> Any | None:
    """Find visible 分享 control (often a plain div row, not role=menuitem)."""
    # Exact text first (Doubao menu rows are frequently non-button nodes).
    found = _first_visible(page.get_by_text("分享", exact=True), limit=20)
    if found is not None:
        return found

    for role in ("menuitem", "button", "menuitemradio", "option", "link"):
        found = _first_visible(page.get_by_role(role, name=sel.SHARE_NAME), limit=20)
        if found is not None:
            return found

    # Menu portal: scope to open menus / popovers.
    for css in ("[role='menu']", "[role='listbox']", "[class*='menu']", "[class*='popover']", "[class*='dropdown']"):
        scope = page.locator(css)
        try:
            n = min(scope.count(), 8)
        except Exception:
            continue
        for i in range(n):
            root = scope.nth(i)
            try:
                if not root.is_visible():
                    continue
            except Exception:
                continue
            hit = _first_visible(root.get_by_text("分享", exact=True), limit=10)
            if hit is not None:
                return hit
            hit = _first_visible(root.get_by_role("menuitem", name=sel.SHARE_NAME), limit=10)
            if hit is not None:
                return hit
    return None


def _iter_more_menu_triggers(page: Any) -> list[Any]:
    """Candidate ⋯ / more buttons; order matters (try header overflow first)."""
    triggers: list[Any] = []
    seen: set[str] = set()

    def _add(el: Any) -> None:
        try:
            if not el.is_visible():
                return
            key = el.evaluate(
                """e => {
                  const r = e.getBoundingClientRect();
                  return [Math.round(r.x), Math.round(r.y), Math.round(r.width), Math.round(r.height)].join(':');
                }"""
            )
        except Exception:
            return
        if not isinstance(key, str) or key in seen:
            return
        seen.add(key)
        triggers.append(el)

    for loc in (
        page.get_by_role("button", name=sel.MORE_MENU_NAME),
        page.locator('button[aria-label*="更多"]'),
        page.locator('button[title*="更多"]'),
        page.locator('[aria-label*="更多"][role="button"]'),
        page.locator('button[aria-haspopup="menu"]'),
    ):
        try:
            n = min(loc.count(), 12)
        except Exception:
            continue
        for i in range(n):
            _add(loc.nth(i))

    # Toolbar near「下载电脑版」: ⋯ is usually left of the download CTA / mute.
    try:
        download = page.get_by_text(re.compile(r"下载电脑版|下载客户端"))
        if download.count() > 0:
            toolbar = download.first.locator("xpath=ancestor::*[self::div or self::header][1]")
            icon_btns = toolbar.locator("button")
            count = icon_btns.count()
            for i in range(count - 1, -1, -1):
                btn = icon_btns.nth(i)
                try:
                    label = (btn.inner_text(timeout=400) or "").strip()
                except Exception:
                    label = ""
                if "下载" in label or len(label) > 6:
                    continue
                _add(btn)
    except Exception:
        logger.debug("more-menu toolbar scan failed", exc_info=True)

    return triggers


def _open_chat_more_menu(page: Any) -> bool:
    """Open conversation ⋯ until 分享 is visible. Do not accept a wrong menu."""
    if _share_menu_open(page):
        return True

    triggers = _iter_more_menu_triggers(page)
    for btn in triggers:
        _dismiss_overlay(page)
        try:
            btn.click(timeout=5_000)
        except Exception:
            continue
        page.wait_for_timeout(500)
        if _share_menu_open(page):
            return True
        # Wrong popup (mute / account) — close and try next trigger.
        _dismiss_overlay(page)

    return False


def _capture_share_url(page: Any) -> str:
    # Current Doubao Web: 分享 sits under header "⋯", not a top-level button.
    share = _locate_share_control(page)
    if share is None:
        if not _open_chat_more_menu(page):
            raise DoubaoShareError("share button not found (could not open ⋯ menu with 分享)")
        share = _locate_share_control(page)
    if share is None:
        raise DoubaoShareError("share button not found (⋯ menu open but no 分享)")

    share.click(timeout=5_000)
    page.wait_for_timeout(800)

    # Prefer explicit copy-link control.
    copy_btn = _first_visible(page.get_by_role("button", name=sel.COPY_LINK_NAME))
    if copy_btn is None:
        copy_btn = _first_visible(page.get_by_text(sel.COPY_LINK_NAME))
    if copy_btn is not None:
        try:
            copy_btn.click(timeout=3_000)
            page.wait_for_timeout(400)
        except Exception:
            logger.debug("copy link click failed", exc_info=True)

    candidates: list[str] = []

    try:
        clip = page.evaluate("navigator.clipboard.readText()")
        if isinstance(clip, str) and clip.strip():
            candidates.append(clip.strip())
    except Exception:
        logger.debug("clipboard read failed", exc_info=True)

    for loc in (
        page.locator("input[value^='http']"),
        page.locator("[role='dialog'] a[href^='http']"),
        page.locator("a[href*='doubao.com']"),
        page.locator("a[href*='/thread/']"),
        page.locator("a[href*='/share']"),
    ):
        try:
            n = min(loc.count(), 12)
            for i in range(n):
                el = loc.nth(i)
                for raw in (el.get_attribute("href"), el.get_attribute("value")):
                    if raw and str(raw).strip().startswith("http"):
                        candidates.append(str(raw).strip())
        except Exception:
            continue

    try:
        dialog = page.locator("[role='dialog']")
        if dialog.count() > 0:
            candidates.extend(extract_urls(dialog.last.inner_text(timeout=2_000) or ""))
    except Exception:
        pass

    # Some builds put the URL in a toast / non-dialog panel after copy.
    try:
        body_urls = extract_urls(page.locator("body").inner_text(timeout=2_000) or "")
        candidates.extend(u for u in body_urls if "/thread/" in u or "/share" in u)
    except Exception:
        pass

    url = pick_share_url(candidates)
    if not url:
        raise DoubaoShareError("could not read share URL from dialog/clipboard")
    return url
