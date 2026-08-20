"""Doubao behavior-captcha detection (main frame + iframes + structure hints)."""

from __future__ import annotations

import logging
import re
from typing import Any

from aperix_geo.services.providers.doubao_web.extract import page_looks_like_captcha
from aperix_geo.services.providers.doubao_web.selectors import (
    CAPTCHA_DOM_SELECTORS,
    CAPTCHA_STRUCTURE_SELECTORS,
)

logger = logging.getLogger(__name__)

# Cross-origin captcha iframes: we often cannot read body text; match src/id/name.
_CAPTCHA_IFRAME_ATTR = re.compile(
    r"captcha|verify|challenge|geetest|hcaptcha|recaptcha|slide|sec\.|"
    r"verifycenter|verification|behavior|puzzle|拖动|拖拽|滑块",
    re.IGNORECASE,
)


def _visible_match(root: Any, selector: str, *, limit: int = 5) -> bool:
    try:
        loc = root.locator(selector)
        n = min(int(loc.count()), limit)
        for i in range(n):
            try:
                if loc.nth(i).is_visible():
                    return True
            except Exception:
                continue
    except Exception:
        return False
    return False


def _frame_roots(page: Any) -> list[Any]:
    roots: list[Any] = [page]
    try:
        main = getattr(page, "main_frame", None)
        for frame in list(getattr(page, "frames", []) or []):
            if frame is None or frame is page or frame is main:
                continue
            roots.append(frame)
    except Exception:
        logger.debug("captcha frame enumerate failed", exc_info=True)
    return roots


def _root_inner_text(root: Any, *, timeout_ms: int = 1_500) -> str:
    try:
        return root.locator("body").inner_text(timeout=timeout_ms) or ""
    except Exception:
        try:
            # Frame may expose content via locator on frame itself.
            return root.inner_text(timeout=timeout_ms) or ""
        except Exception:
            return ""


def _iframe_attrs_look_like_captcha(page: Any) -> bool:
    """Detect captcha host iframes even when cross-origin body is unreadable."""
    try:
        iframes = page.locator("iframe")
        n = min(int(iframes.count()), 25)
    except Exception:
        return False
    for i in range(n):
        el = iframes.nth(i)
        try:
            if not el.is_visible():
                continue
        except Exception:
            continue
        blob_parts: list[str] = []
        for attr in ("src", "id", "name", "title", "aria-label"):
            try:
                blob_parts.append(str(el.get_attribute(attr) or ""))
            except Exception:
                continue
        blob = " ".join(blob_parts)
        if _CAPTCHA_IFRAME_ATTR.search(blob):
            return True
    return False


def page_shows_behavior_captcha(page: Any) -> bool:
    """True when Doubao behavior captcha / network-risk UI is present.

    Checks:
    1. Visible text on main document and same-origin frames (CAPTCHA_TEXT)
    2. Visible text nodes via CAPTCHA_DOM_SELECTORS on each frame
    3. Structural captcha containers / iframe src hints on the main page
    """
    if page is None:
        return False

    for root in _frame_roots(page):
        text = _root_inner_text(root)
        if page_looks_like_captcha(text):
            return True
        for selector in CAPTCHA_DOM_SELECTORS:
            if _visible_match(root, selector):
                return True

    if _iframe_attrs_look_like_captcha(page):
        return True

    for selector in CAPTCHA_STRUCTURE_SELECTORS:
        if _visible_match(page, selector, limit=8):
            return True

    return False
