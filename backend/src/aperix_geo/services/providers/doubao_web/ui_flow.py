"""Doubao Web UI flow: blank chat → send → wait → extract → share_url."""

from __future__ import annotations

import logging
import os
import random
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
from aperix_geo.services.providers.doubao_web.runtime import (
    assert_no_captcha,
    assert_no_system_error,
    ensure_chat_mode as _ensure_chat_mode,
    page_has_system_error,
    wait_for_composer,
)

logger = logging.getLogger(__name__)

_STABLE_IDLE_POLLS = 10  # ~3s of unchanged assistant text when stop/streaming is missing

# Random pause (ms) between UI steps — jitter reduces burst traffic vs Doubao rate limits.
_HUMAN_PAUSE_MS = (250, 500)


def _human_pause(page: Any) -> int:
    """Sleep a random duration (ms); returns chosen delay."""
    lo, hi = _HUMAN_PAUSE_MS
    ms = random.randint(lo, hi)
    page.wait_for_timeout(ms)
    return ms


def ensure_blank_chat(page: Any, *, base_url: str, attempts: int = 2) -> None:
    """Open a blank session and hard-validate before sending the sample prompt.

    Always click「新对话」(even on /chat/), then switch off「工作」if needed.
    """
    prior_id = conversation_id_from_url(page.url or "")
    last_reason = ""
    for attempt in range(1, max(1, attempts) + 1):
        _open_fresh_chat(page, base_url=base_url)
        _human_pause(page)
        last_reason = _probe_blank_chat_reason(page, prior_conversation_id=prior_id)
        if not last_reason:
            logger.info(
                "blank chat ready attempt=%s url=%s prior_id=%s",
                attempt,
                page.url,
                prior_id or "-",
            )
            _human_pause(page)
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


def _click_new_chat(page: Any) -> bool:
    try:
        page.get_by_role("button", name=sel.NEW_CHAT_NAME).first.wait_for(
            state="visible", timeout=5_000
        )
    except Exception:
        pass
    btn = page.get_by_role("button", name=sel.NEW_CHAT_NAME)
    if btn.count() == 0:
        btn = page.get_by_text(sel.NEW_CHAT_NAME)
    if btn.count() == 0:
        logger.warning("doubao 新对话 button not found url=%s", page.url)
        return False
    try:
        btn.first.click(timeout=5_000)
        _human_pause(page)
        logger.info("doubao clicked 新对话 url=%s", page.url)
        return True
    except Exception:
        logger.debug("new chat click skipped", exc_info=True)
        return False


def _open_fresh_chat(page: Any, *, base_url: str) -> None:
    """Land on /chat, click「新对话」, then switch to「对话」if still on「工作」."""
    target = (base_url or sel.CHAT_URL).strip() or sel.CHAT_URL

    if conversation_id_from_url(page.url or ""):
        try:
            page.goto(target, wait_until="domcontentloaded")
            _human_pause(page)
        except Exception:
            logger.debug("goto chat landing failed", exc_info=True)

    _click_new_chat(page)

    # If still on a concrete thread URL, force landing again (stronger than click alone).
    if conversation_id_from_url(page.url or ""):
        try:
            page.goto(target, wait_until="domcontentloaded")
            _human_pause(page)
        except Exception:
            logger.debug("second goto blank chat failed", exc_info=True)

    _ensure_chat_mode(page)


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
    from aperix_geo.services.providers.doubao_web.runtime import _composer as _visible_composer

    return _visible_composer(page)


def _fill_and_send(page: Any, prompt: str, *, base_url: str = "") -> None:
    box = wait_for_composer(page, base_url=base_url)
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

    _human_pause(page)

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
    system_error = False
    composer = False
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
        system_error = bool(page_has_system_error(page))
    except Exception:
        pass
    try:
        composer = _composer(page) is not None
    except Exception:
        pass
    try:
        body_head = (page.locator("body").inner_text(timeout=1_500) or "").strip()
        body_head = re.sub(r"\s+", " ", body_head)[:240]
    except Exception:
        body_head = ""
    return (
        f"url={url!r} conv_id={conv or '-'} stop={stop} streaming={streaming} "
        f"md_box={md_n} action_bar={action} composer={composer} "
        f"captcha={captcha} system_error={system_error} body={body_head!r}"
    )


def _debug_screenshot(page: Any, *, label: str) -> str:
    """Best-effort PNG on the Playwright worker thread. Returns path or ''."""
    raw = (os.environ.get("GEO_WEB_CRAWL_DEBUG_SHOT_DIR") or "").strip()
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


def _wait_send_accepted(
    page: Any,
    *,
    prior_conv_id: str,
    deadline: float,
    require_new_conversation: bool = False,
) -> None:
    """After send: require conversation id and/or generating UI, else fail fast with snapshot."""

    def _accepted() -> bool:
        conv = conversation_id_from_url(getattr(page, "url", "") or "")
        if require_new_conversation:
            return bool(conv and conv != prior_conv_id)
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
        from aperix_geo.services.providers.doubao_web.runtime import assert_logged_in

        assert_logged_in(page)
        assert_no_captcha(page)
        assert_no_system_error(page)
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
    return _message_action_bar(page) is not None


def _wait_until(page: Any, *, deadline: float, predicate: Any, label: str) -> None:
    """Poll DOM until predicate() is true, or raise on crawl deadline / page closed."""
    while time.monotonic() < deadline:
        # Session can die mid-wait (Doubao lands on ?from_logout=1).
        from aperix_geo.services.providers.doubao_web.runtime import assert_logged_in

        assert_logged_in(page)
        assert_no_captcha(page)
        assert_no_system_error(page)
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


def _last_assistant_md_text(page: Any, *, user_prompt: str = "") -> str:
    """Last ``.md-box-root`` body that is not just the user prompt echo."""
    prompt = (user_prompt or "").strip()
    try:
        loc = page.locator(".md-box-root")
        n = int(loc.count())
    except Exception:
        return ""
    for i in range(n - 1, -1, -1):
        target = loc.nth(i)
        try:
            if not target.is_visible():
                continue
            text = (target.inner_text(timeout=800) or "").strip()
        except Exception:
            continue
        if not text:
            continue
        if prompt and text == prompt:
            continue
        return text
    return ""


def _wait_generation_done(
    page: Any,
    *,
    settings: Settings,
    deadline: float,
    user_prompt: str = "",
) -> None:
    """Wait until the assistant reply is actually idle — not the user-message toolbar.

    Doubao shows ``.message-action-button-main`` on the *user* bubble right after
    send. Treating that as "generation finished" copies an empty/prompt clipboard
    and raises ``empty assistant reply``.

    Finish requires assistant ``.md-box-root`` text (not equal to the prompt) and
    either: stop/streaming went idle, or that text stayed unchanged for ~3s.
    """
    _ = settings
    saw_generating_ui = False
    last_text = ""
    stable_polls = 0

    def _started() -> bool:
        nonlocal saw_generating_ui, last_text
        generating = _stop_button_visible(page) or _any_streaming_true(page)
        text = _last_assistant_md_text(page, user_prompt=user_prompt)
        if generating:
            saw_generating_ui = True
            last_text = text
            return True
        if text:
            last_text = text
            return True
        return False

    _wait_until(
        page,
        deadline=deadline,
        predicate=_started,
        label="generation start (stop button, streaming, or assistant md-box)",
    )

    def _finished() -> bool:
        nonlocal saw_generating_ui, last_text, stable_polls
        generating = _stop_button_visible(page) or _any_streaming_true(page)
        text = _last_assistant_md_text(page, user_prompt=user_prompt)
        if generating:
            saw_generating_ui = True
            last_text = text
            stable_polls = 0
            return False
        if not text:
            stable_polls = 0
            return False
        if saw_generating_ui:
            return True
        if text == last_text:
            stable_polls += 1
        else:
            last_text = text
            stable_polls = 0
        return stable_polls >= _STABLE_IDLE_POLLS

    _wait_until(
        page,
        deadline=deadline,
        predicate=_finished,
        label="generation end (idle after stop/streaming + assistant text)",
    )


def _read_clipboard(page: Any) -> str:
    try:
        clip = page.evaluate("navigator.clipboard.readText()")
    except Exception:
        logger.debug("clipboard read failed", exc_info=True)
        return ""
    return clip.strip() if isinstance(clip, str) else ""


def _message_action_bar(page: Any) -> Any | None:
    """First visible ``.message-action-button-main``."""
    bar = _first_visible(
        page.locator(sel.MESSAGE_ACTION_BAR),
        limit=30,
    )
    if bar is None:
        return None
    try:
        bar.wait_for(state="visible", timeout=3_000)
    except Exception:
        return None
    return bar


def _locate_copy_body_button(bar: Any) -> Any | None:
    """First direct child button = 复制正文."""
    try:
        direct = bar.locator(":scope > button")
        if direct.count() > 0:
            return direct.first
    except Exception:
        pass
    return None


def _copy_assistant_markdown_via_toolbar(page: Any) -> str:
    """Click the first toolbar's first button (复制正文) and read clipboard Markdown."""
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


def _extract_assistant_text(
    page: Any,
    *,
    deadline: float | None = None,
    user_prompt: str = "",
) -> str:
    """Copy assistant body via first ``.message-action-button-main`` → first ``button`` only."""
    _ = deadline  # reserved; completion is decided in _wait_generation_done
    prompt = (user_prompt or "").strip()
    copied = _copy_assistant_markdown_via_toolbar(page)
    if copied.strip() and copied.strip() != prompt:
        return copied.strip()
    return ""


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


def _is_search_panel_header(el: Any) -> bool:
    """True for the collapsible「搜索 N 个关键词」row — clicking again toggles closed."""
    try:
        text = (el.inner_text(timeout=400) or "").strip()
    except Exception:
        return False
    return bool(sel.SEARCH_PANEL_HINT.search(text))


def _extract_search_panel(page: Any) -> tuple[str, tuple[str, ...]]:
    """Match panel header by regex text, expand once, then switch inner tabs."""
    hint = _first_visible(page.get_by_text(sel.SEARCH_PANEL_HINT), limit=20)
    if hint is None:
        return "", ()

    try:
        hint.click(timeout=2_000)
        page.wait_for_timeout(500)
    except Exception:
        logger.debug("search panel expand click failed", exc_info=True)

    root = _panel_root(hint)

    # Exact tab labels only — bare「关键词」matches the header and collapses the panel.
    for tab_pattern in (re.compile(r"^搜索关键词$"), re.compile(r"^参考资料$")):
        try:
            tab = root.get_by_text(tab_pattern)
            found = _first_visible(tab, limit=6)
            if found is None or _is_search_panel_header(found):
                continue
            found.click(timeout=2_000)
            page.wait_for_timeout(400)
        except Exception:
            continue

    try:
        text = (root.inner_text(timeout=3_000) or "").strip()
    except Exception:
        text = ""

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
    if _conversation_share_menu_open(page):
        return True
    return _locate_share_control(page) is not None


def _conversation_overflow_menus(page: Any) -> Any:
    """Radix dropdown portals for conversation-level overflow (header ⋯)."""
    return page.locator(sel.DROPDOWN_MENU_CONTENT)


def _menu_has_share_row(root: Any) -> bool:
    try:
        if not root.is_visible():
            return False
    except Exception:
        return False
    try:
        body = (root.inner_text(timeout=800) or "").strip()
    except Exception:
        return False
    return "分享" in body and bool(sel.SHARE_MENU_HINT.search(body))


def _share_row_in_menu(root: Any) -> Any | None:
    """Return the 分享 row inside a conversation overflow menu."""
    if not _menu_has_share_row(root):
        return None
    hit = _first_visible(root.get_by_text("分享", exact=True), limit=6)
    if hit is not None:
        return hit
    return _first_visible(root.get_by_role("menuitem", name=sel.SHARE_NAME), limit=6)


def _locate_share_control(page: Any) -> Any | None:
    """Find visible 分享 in the conversation header overflow menu."""
    for root in _iter_visible_locators(_conversation_overflow_menus(page), limit=8):
        hit = _share_row_in_menu(root)
        if hit is not None:
            return hit

    for css in ("[role='menu']", "[role='listbox']"):
        for root in _iter_visible_locators(page.locator(css), limit=8):
            hit = _share_row_in_menu(root)
            if hit is not None:
                return hit
    return None


def _iter_visible_locators(locator: Any, *, limit: int) -> list[Any]:
    out: list[Any] = []
    try:
        n = min(int(locator.count()), limit)
    except Exception:
        return out
    for i in range(n):
        el = locator.nth(i)
        try:
            if el.is_visible():
                out.append(el)
        except Exception:
            continue
    return out


def _more_menu_button(page: Any) -> Any | None:
    """Conversation header overflow (⋯) in the main column top bar."""
    main = page.locator(sel.CHAT_MAIN)
    for loc in (
        main.locator(sel.CHAT_HEADER_MORE_TRIGGER),
        main.locator(
            f'button[data-slot="dropdown-menu-trigger"]:has('
            f'[aria-label="{sel.MORE_ARIA_LABEL}"])'
        ),
        main.locator(f'button[aria-label="{sel.MORE_ARIA_LABEL}"]'),
    ):
        found = _first_visible(loc, limit=4)
        if found is not None:
            return found
    return None


def _conversation_share_menu_open(page: Any) -> bool:
    """True when the header overflow menu (分享 + 删除/置顶…) is open."""
    for root in _iter_visible_locators(_conversation_overflow_menus(page), limit=8):
        if _menu_has_share_row(root):
            return True
    for css in ("[role='menu']",):
        for root in _iter_visible_locators(page.locator(css), limit=8):
            if _menu_has_share_row(root):
                return True
    return False


def _activate_header_more_button(page: Any, btn: Any) -> None:
    """Header ⋯ uses Radix hover trigger — hover then click the outer menu trigger."""
    try:
        btn.hover(timeout=3_000)
        _human_pause(page)
    except Exception:
        logger.debug("doubao share: 更多 hover failed", exc_info=True)
    btn.click(timeout=5_000)
    try:
        page.locator(f"{sel.DROPDOWN_MENU_CONTENT}[data-state='open']").first.wait_for(
            state="visible",
            timeout=2_500,
        )
    except Exception:
        pass


def _open_chat_more_menu(page: Any) -> bool:
    """Open conversation ⋯ until 分享 is visible."""
    if _share_menu_open(page):
        return True

    btn = _more_menu_button(page)
    if btn is None:
        logger.warning(
            "doubao share: header 更多 button not found url=%s",
            getattr(page, "url", ""),
        )
        return False

    _dismiss_overlay(page)
    try:
        _activate_header_more_button(page, btn)
    except Exception:
        logger.warning("doubao share: 更多 button click failed", exc_info=True)
        return False
    _human_pause(page)
    if not _share_menu_open(page):
        logger.warning(
            "doubao share: 更多 menu opened but no 分享 row url=%s",
            getattr(page, "url", ""),
        )
    return _share_menu_open(page)


def capture_share_url(page: Any) -> str:
    # 分享 sits under header button[aria-label="更多"].
    share = _locate_share_control(page)
    if share is None:
        if not _open_chat_more_menu(page):
            raise DoubaoShareError("share button not found (could not open ⋯ menu with 分享)")
        share = _locate_share_control(page)
    if share is None:
        raise DoubaoShareError("share button not found (⋯ menu open but no 分享)")

    share.click(timeout=5_000)
    _human_pause(page)

    # Prefer explicit copy-link control.
    copy_btn = _first_visible(page.get_by_role("button", name=sel.COPY_LINK_NAME))
    if copy_btn is None:
        copy_btn = _first_visible(page.get_by_text(sel.COPY_LINK_NAME))
    if copy_btn is not None:
        try:
            copy_btn.click(timeout=3_000)
            _human_pause(page)
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


def try_capture_share_url(page: Any) -> str:
    """Best-effort share URL; empty string when the control/clipboard path fails."""
    _human_pause(page)
    try:
        return (capture_share_url(page) or "").strip()
    except DoubaoShareError as exc:
        logger.warning(
            "doubao share_url capture failed: %s url=%s",
            exc,
            getattr(page, "url", ""),
        )
        return ""
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "doubao share_url capture failed: %s url=%s",
            exc,
            getattr(page, "url", ""),
        )
        return ""


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
