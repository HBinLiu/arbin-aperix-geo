"""Doubao Web UI flow: blank chat → send → wait → extract → share_url."""

from __future__ import annotations

import logging
import os
import re
import time
from pathlib import Path
from typing import Any

from aperix_geo.config import Settings
from aperix_geo.services.providers._helpers import dedupe_urls
from aperix_geo.services.providers.doubao_web import selectors as sel
from aperix_geo.services.providers.doubao_web.errors import (
    DoubaoCrawlError,
    DoubaoNeedsHumanOps,
    DoubaoShareError,
)
from aperix_geo.services.providers.doubao_web.extract import (
    blank_chat_failure_reason,
    conversation_id_from_url,
    extract_urls,
    panel_present,
    pick_share_url,
)
from aperix_geo.services.providers.doubao_web.runtime import assert_no_captcha

logger = logging.getLogger(__name__)


def _ensure_blank_chat(page: Any, *, base_url: str, attempts: int = 2) -> None:
    """Open a blank session and hard-validate before sending the sample prompt.

    If the landing URL already has no conversation id, skip「新对话」on the first
    attempt. Retries force goto + 新对话 when the page is still dirty.
    """
    prior_id = conversation_id_from_url(page.url or "")
    last_reason = ""
    for attempt in range(1, max(1, attempts) + 1):
        current_id = conversation_id_from_url(page.url or "")
        # Initial open already on /chat/ with empty id → do not click 新对话.
        click_new = bool(current_id) or attempt > 1
        _open_fresh_chat(page, base_url=base_url, click_new_chat=click_new)
        page.wait_for_timeout(500)
        last_reason = _probe_blank_chat_reason(page, prior_conversation_id=prior_id)
        if not last_reason:
            logger.info(
                "blank chat ready attempt=%s url=%s prior_id=%s clicked_new=%s",
                attempt,
                page.url,
                prior_id or "-",
                click_new,
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


def _open_fresh_chat(page: Any, *, base_url: str, click_new_chat: bool = True) -> None:
    """Navigate to chat landing; click 新对话 only when requested or still on a thread."""
    target = (base_url or sel.CHAT_URL).strip() or sel.CHAT_URL

    # Already on blank /chat/ and caller does not force refresh → nothing to do.
    if not click_new_chat and not conversation_id_from_url(page.url or ""):
        logger.info("blank chat landing already (empty conversation_id); skip 新对话 url=%s", page.url)
        return

    try:
        page.goto(target, wait_until="domcontentloaded")
        page.wait_for_timeout(400)
    except Exception:
        logger.debug("goto chat landing failed", exc_info=True)

    # After goto landing with empty id and not forcing click → done.
    if not click_new_chat and not conversation_id_from_url(page.url or ""):
        return

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
    try:
        box.fill("")
        box.fill(prompt)
    except Exception:
        # Some Doubao builds reject fill() on contenteditable; fall back to typing.
        logger.debug("composer fill failed; typing prompt", exc_info=True)
        try:
            box.press("ControlOrMeta+a")
            box.press("Backspace")
        except Exception:
            pass
        page.keyboard.type(prompt, delay=15)

    send = page.get_by_role("button", name=sel.SEND_NAME)
    if send.count() == 0:
        send = page.locator("button").filter(has_text=sel.SEND_NAME)
    if send.count() > 0:
        try:
            send.last.click(timeout=5_000)
            return
        except Exception:
            logger.debug("send button click failed; trying Enter", exc_info=True)
    box.press("Enter")


def _page_debug_summary(page: Any) -> str:
    """Compact page signals for timeout / send failures (safe for logs)."""
    url = ""
    try:
        url = str(getattr(page, "url", "") or "")
    except Exception:
        url = ""
    conv = conversation_id_from_url(url)
    stop = False
    streaming = False
    md_n = 0
    action = False
    captcha = False
    body_head = ""
    try:
        stop = _stop_button_visible(page)
    except Exception:
        pass
    try:
        streaming = _any_streaming_true(page)
    except Exception:
        pass
    try:
        md_n = int(page.locator(".md-box-root").count())
    except Exception:
        md_n = 0
    try:
        action = _action_bar_visible(page)
    except Exception:
        pass
    try:
        from aperix_geo.services.providers.doubao_web.runtime import page_has_captcha

        captcha = bool(page_has_captcha(page))
    except Exception:
        pass
    try:
        body_head = (page.locator("body").inner_text(timeout=1_500) or "").strip()
        body_head = re.sub(r"\s+", " ", body_head)[:240]
    except Exception:
        body_head = ""
    return (
        f"url={url!r} conv_id={conv or '-'} stop={stop} streaming={streaming} "
        f"md_box={md_n} action_bar={action} captcha={captcha} body={body_head!r}"
    )


def _debug_screenshot(page: Any, *, label: str) -> str:
    """Best-effort PNG on the Playwright worker thread. Returns path or ''."""
    raw = (os.environ.get("GEO_WEB_CRAWL_LIVE_VIEW_SCREENSHOT_DIR") or "").strip()
    if not raw:
        raw = (os.environ.get("GEO_WEB_CRAWL_DEBUG_SHOT_DIR") or "").strip()
    # Compose mounts ./live-shots → /tmp/geo-crawl-live; use when present so
    # timeout diagnostics work without turning on LIVE_VIEW pause.
    if not raw and Path("/tmp/geo-crawl-live").is_dir():
        raw = "/tmp/geo-crawl-live"
    if not raw:
        return ""
    try:
        directory = Path(raw)
        directory.mkdir(parents=True, exist_ok=True)
        stamp = time.strftime("%H%M%S")
        path = directory / f"debug-{label}-{stamp}.png"
        page.screenshot(path=str(path), full_page=False)
        logger.warning("doubao crawl debug screenshot → %s", path)
        return str(path)
    except Exception:
        logger.info("doubao crawl debug screenshot failed label=%s", label, exc_info=True)
        return ""


def _wait_send_accepted(page: Any, *, prior_conv_id: str, deadline: float) -> None:
    """After send: require conversation id and/or generating UI, else fail fast with snapshot."""

    def _accepted() -> bool:
        conv = conversation_id_from_url(getattr(page, "url", "") or "")
        if conv and conv != prior_conv_id:
            return True
        if _stop_button_visible(page) or _any_streaming_true(page):
            return True
        if _action_bar_visible(page):
            return True
        try:
            if page.locator(".md-box-root").count() > 0:
                return True
        except Exception:
            pass
        return False

    while time.monotonic() < deadline:
        assert_no_captcha(page)
        if _accepted():
            return
        page.wait_for_timeout(300)
    shot = _debug_screenshot(page, label="send-not-accepted")
    detail = _page_debug_summary(page)
    raise DoubaoCrawlError(
        "send not accepted (no new conversation id / generating UI); "
        f"{detail}"
        + (f" shot={shot}" if shot else "")
    )


def _stop_button_visible(page: Any) -> bool:
    """True while Doubao shows stop-generation control (label / aria / text)."""
    for locator in (
        page.get_by_role("button", name=sel.STOP_NAME),
        page.locator("button").filter(has_text=sel.STOP_NAME),
        page.locator("button[aria-label]").filter(has_text=sel.STOP_NAME),
    ):
        try:
            n = min(locator.count(), 8)
            for i in range(n):
                el = locator.nth(i)
                if el.is_visible():
                    return True
        except Exception:
            continue
    # Fallback: scan visible button labels (Doubao sometimes uses icon + aria only).
    try:
        return bool(
            page.evaluate(
                """() => {
                  const re = /停止生成|停止回答|停止输出|^停止$|Stop generating/i;
                  for (const b of document.querySelectorAll('button')) {
                    const style = window.getComputedStyle(b);
                    if (style.display === 'none' || style.visibility === 'hidden') continue;
                    if (b.getClientRects().length === 0) continue;
                    const label = (
                      b.getAttribute('aria-label') ||
                      b.getAttribute('title') ||
                      b.innerText ||
                      ''
                    ).trim();
                    if (re.test(label)) return true;
                  }
                  return false;
                }"""
            )
        )
    except Exception:
        return False


def _any_streaming_true(page: Any) -> bool:
    """True if any node still has data-streaming=true (not only the last md-box)."""
    try:
        return page.locator('[data-streaming="true"]').count() > 0
    except Exception:
        return False


def _action_bar_visible(page: Any) -> bool:
    bar = page.locator(sel.MESSAGE_ACTION_BAR)
    try:
        if bar.count() <= 0:
            return False
        return bool(bar.last.is_visible())
    except Exception:
        return False


def _wait_until(page: Any, *, deadline: float, predicate: Any, label: str) -> None:
    """Poll DOM until predicate() is true, or raise on crawl deadline / page closed."""
    while time.monotonic() < deadline:
        assert_no_captcha(page)
        try:
            if predicate():
                return
        except DoubaoNeedsHumanOps:
            raise
        except Exception as exc:
            name = type(exc).__name__
            if "TargetClosed" in name or "closed" in str(exc).lower():
                raise DoubaoCrawlError(f"page closed while waiting for {label}") from exc
        try:
            page.wait_for_timeout(300)
        except Exception as exc:
            name = type(exc).__name__
            if "TargetClosed" in name or "closed" in str(exc).lower():
                raise DoubaoCrawlError(f"page closed while waiting for {label}") from exc
            raise
    shot = _debug_screenshot(page, label=label.replace(" ", "-")[:40])
    detail = _page_debug_summary(page)
    raise DoubaoCrawlError(
        f"timeout waiting for {label}; {detail}"
        + (f" shot={shot}" if shot else "")
    )


def _wait_generation_done(page: Any, *, settings: Settings, deadline: float) -> None:
    """Wait for full reply via generating → idle → toolbar (DOM only).

    Doubao may show ``.message-action-button-main`` before the answer finishes.
    Therefore finish requires having observed a real generating signal first:

      1. 停止按钮 / streaming / md-box / action bar 任一出现（生成已开始或已极快结束）
      2. 停止消失 且 页面上不再有 ``data-streaming=true``
      3. ``.message-action-button-main`` 可见 → 再复制
    """
    _ = settings
    saw_generating = False

    def _generating() -> bool:
        return _stop_button_visible(page) or _any_streaming_true(page)

    def _started() -> bool:
        nonlocal saw_generating
        if _generating():
            saw_generating = True
            return True
        # Ultra-fast replies may skip a visible stop control.
        try:
            if page.locator(".md-box-root").count() > 0:
                saw_generating = True
                return True
        except Exception:
            pass
        if _action_bar_visible(page):
            saw_generating = True
            return True
        return False

    _wait_until(
        page,
        deadline=deadline,
        predicate=_started,
        label="generation start (stop button or data-streaming=true)",
    )

    def _finished() -> bool:
        nonlocal saw_generating
        if _generating():
            saw_generating = True
            return False
        if not saw_generating:
            return False
        return _action_bar_visible(page)

    _wait_until(
        page,
        deadline=deadline,
        predicate=_finished,
        label="generation end (idle after stop/streaming + action bar)",
    )


def _read_clipboard(page: Any) -> str:
    try:
        clip = page.evaluate("navigator.clipboard.readText()")
    except Exception:
        logger.debug("clipboard read failed", exc_info=True)
        return ""
    return clip.strip() if isinstance(clip, str) else ""


def _message_action_bar(page: Any) -> Any | None:
    """Latest visible ``.message-action-button-main`` under the assistant reply."""
    bar = page.locator(sel.MESSAGE_ACTION_BAR)
    try:
        if bar.count() <= 0:
            return None
        target = bar.last
        target.wait_for(state="visible", timeout=5_000)
        return target
    except Exception:
        return None


def _locate_copy_body_button(bar: Any) -> Any | None:
    """First toolbar button = 复制正文 (sibling before「朗读」when present)."""
    try:
        read_aloud = bar.get_by_role("button", name=sel.READ_ALOUD_NAME)
        if read_aloud.count() > 0:
            prev = read_aloud.first.locator("xpath=preceding-sibling::button[1]")
            if prev.count() > 0:
                return prev.first
    except Exception:
        pass
    try:
        direct = bar.locator(":scope > button")
        if direct.count() > 0:
            return direct.first
    except Exception:
        pass
    return None


def _copy_assistant_markdown_via_toolbar(page: Any) -> str:
    """Click 复制正文 once and return clipboard Markdown (call after generation done)."""
    bar = _message_action_bar(page)
    if bar is None:
        return ""
    copy_btn = _locate_copy_body_button(bar)
    if copy_btn is None:
        return ""
    before = _read_clipboard(page)
    try:
        copy_btn.click(timeout=5_000)
        page.wait_for_timeout(400)
    except Exception:
        logger.debug("assistant copy-button click failed", exc_info=True)
        return ""
    after = _read_clipboard(page)
    if not after:
        return ""
    if after != before:
        return after
    if after.strip().lower().startswith("http") and len(after.strip().split()) == 1:
        return ""
    return after


def _extract_assistant_text(page: Any, *, deadline: float | None = None) -> str:
    """Prefer toolbar「复制」→ clipboard Markdown; fallback ``md-box-root``."""
    from aperix_geo.services.providers.doubao_web.extract import md_box_html_to_markdown

    _ = deadline  # reserved; completion is decided in _wait_generation_done
    copied = _copy_assistant_markdown_via_toolbar(page)
    if copied.strip():
        return copied.strip()

    for css in sel.MD_BOX_SELECTORS:
        loc = page.locator(css)
        try:
            n = loc.count()
        except Exception:
            continue
        if n <= 0:
            continue
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


def capture_share_url(page: Any) -> str:
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
        clip = _read_clipboard(page)
        if clip:
            candidates.append(clip)
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


def _stop_generation_if_running(page: Any) -> None:
    if not _stop_button_visible(page):
        return
    for loc in (
        page.get_by_role("button", name=sel.STOP_NAME),
        page.locator("button").filter(has_text=sel.STOP_NAME),
    ):
        btn = _first_visible(loc, limit=8)
        if btn is None:
            continue
        try:
            btn.click(timeout=3_000)
            page.wait_for_timeout(500)
            return
        except Exception:
            continue


def _locate_delete_control(page: Any) -> Any | None:
    """Find visible 删除 row in an open overflow menu (not generic page chrome)."""
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
            hit = _first_visible(root.get_by_text(sel.DELETE_CHAT_NAME), limit=10)
            if hit is not None:
                return hit
            for role in ("menuitem", "button", "option"):
                hit = _first_visible(root.get_by_role(role, name=sel.DELETE_CHAT_NAME), limit=10)
                if hit is not None:
                    return hit

    found = _first_visible(page.get_by_text(sel.DELETE_CHAT_NAME), limit=20)
    if found is not None:
        return found
    for role in ("menuitem", "button"):
        found = _first_visible(page.get_by_role(role, name=sel.DELETE_CHAT_NAME), limit=20)
        if found is not None:
            return found
    return None


def _delete_menu_open(page: Any) -> bool:
    return _locate_delete_control(page) is not None


def _open_chat_delete_menu(page: Any) -> bool:
    """Open conversation ⋯ until 删除 is visible."""
    if _delete_menu_open(page):
        return True
    # Share menu is the same overflow; opening it also exposes 删除.
    if _open_chat_more_menu(page) and _delete_menu_open(page):
        return True

    triggers = _iter_more_menu_triggers(page)
    for btn in triggers:
        _dismiss_overlay(page)
        try:
            btn.click(timeout=5_000)
        except Exception:
            continue
        page.wait_for_timeout(500)
        if _delete_menu_open(page):
            return True
        _dismiss_overlay(page)
    return False


def _confirm_delete_dialog(page: Any) -> bool:
    for loc in (
        page.get_by_role("button", name=sel.CONFIRM_DELETE_NAME),
        page.locator("[role='dialog'] button").filter(has_text=sel.CONFIRM_DELETE_NAME),
        page.get_by_text(sel.CONFIRM_DELETE_NAME),
    ):
        btn = _first_visible(loc, limit=12)
        if btn is None:
            continue
        try:
            btn.click(timeout=3_000)
            page.wait_for_timeout(600)
            return True
        except Exception:
            continue
    return False


def delete_current_conversation(page: Any, *, require: bool = True) -> None:
    """Delete the thread currently open in the URL (heartbeat probe cleanup).

    No-op when URL has no conversation id. When ``require`` and a id was present,
    raises ``DoubaoCrawlError`` if the thread is still open after attempts.
    """
    conv_id = conversation_id_from_url(page.url or "")
    if not conv_id:
        logger.info("delete conversation skipped (no conversation id) url=%s", page.url)
        return

    _stop_generation_if_running(page)
    _dismiss_overlay(page)

    deleted = False
    if _open_chat_delete_menu(page):
        control = _locate_delete_control(page)
        if control is not None:
            try:
                control.click(timeout=5_000)
                page.wait_for_timeout(400)
                _confirm_delete_dialog(page)
                deleted = True
            except Exception:
                logger.debug("delete menu click failed", exc_info=True)

    deadline = time.monotonic() + 8.0
    while time.monotonic() < deadline:
        current = conversation_id_from_url(page.url or "")
        if current != conv_id:
            logger.info("deleted probe conversation id=%s now_url=%s", conv_id, page.url)
            return
        try:
            page.wait_for_timeout(300)
        except Exception:
            break

    msg = f"failed to delete probe conversation id={conv_id} url={page.url} clicked={deleted}"
    if require:
        raise DoubaoCrawlError(msg)
    logger.warning(msg)
