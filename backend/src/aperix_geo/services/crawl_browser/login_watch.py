"""Login-complete heuristics shared by geo-web-crawl in-process watchers.

Keep this free of SQLAlchemy / Celery. Cookie name sets live in crawl_accounts.cookies.
"""

from __future__ import annotations

import re
from typing import Any

from aperix_geo.services.crawl_accounts.cookies import (
    login_proof_cookie_names_for_platform,
    session_cookie_names_for_platform,
)

_LOGIN_CTA = re.compile(r"登录")
_LOGGED_OUT_URL = re.compile(r"/passport|/login(?:/|\?|$)|from_logout=1", re.I)
_CAPTCHA_TEXT = re.compile(
    r"拖拽到这里|请选择所有符合|行为验证|人机验证|安全验证|滑动验证|"
    r"选中所有|拖拽到下方|完成验证后继续"
)
_CAPTCHA_SELECTORS = (
    "text=拖拽到这里",
    "text=请选择所有符合上文描述的图片",
    "text=行为验证",
    "text=人机验证",
    "text=安全验证",
)


def _session_cookie_pairs(platform: str, state: dict[str, Any]) -> list[tuple[str, str]]:
    cookies = state.get("cookies") or []
    wanted = session_cookie_names_for_platform(platform) or None
    pairs: list[tuple[str, str]] = []
    for cookie in cookies:
        if not isinstance(cookie, dict):
            continue
        name = str(cookie.get("name") or "")
        value = str(cookie.get("value") or "").strip()
        if not value:
            continue
        if wanted is not None:
            if name in wanted:
                pairs.append((name, value))
        elif name.startswith("session") or name.startswith("sid_"):
            pairs.append((name, value))
    return pairs


def session_cookie_names(platform: str, state: dict[str, Any]) -> list[str]:
    return sorted({name for name, _ in _session_cookie_pairs(platform, state)})


def login_proof_cookie_names(platform: str, state: dict[str, Any]) -> list[str]:
    names = session_cookie_names(platform, state)
    proof = login_proof_cookie_names_for_platform(platform)
    if not proof:
        return names
    return [n for n in names if n in proof]


def session_fingerprint(platform: str, state: dict[str, Any]) -> tuple[tuple[str, str], ...]:
    return tuple(sorted(_session_cookie_pairs(platform, state)))


def baseline_fingerprint(platform: str, state: dict[str, Any] | None) -> tuple[tuple[str, str], ...]:
    if not isinstance(state, dict):
        return ()
    return session_fingerprint(platform, state)


def page_shows_login_ui(page: Any) -> bool:
    if page is None:
        return True
    url = str(getattr(page, "url", "") or "")
    if _LOGGED_OUT_URL.search(url):
        return True
    try:
        for role in ("button", "link"):
            loc = page.get_by_role(role, name=_LOGIN_CTA)
            n = min(int(loc.count()), 8)
            for i in range(n):
                el = loc.nth(i)
                if not el.is_visible():
                    continue
                label = ""
                try:
                    label = (el.inner_text(timeout=800) or "").strip()
                except Exception:
                    label = ""
                if re.search(r"^\s*登录\s*$", label or "登录"):
                    return True
    except Exception:
        pass
    return False


def page_has_captcha(page: Any) -> bool:
    try:
        body = page.locator("body").inner_text(timeout=2_000) or ""
    except Exception:
        body = ""
    if _CAPTCHA_TEXT.search(body):
        return True
    for css in _CAPTCHA_SELECTORS:
        try:
            loc = page.locator(css)
            n = min(loc.count(), 5)
            for i in range(n):
                if loc.nth(i).is_visible():
                    return True
        except Exception:
            continue
    return False


def ready_for_complete(
    *,
    reason: str,
    has_session: bool,
    fingerprint: tuple[tuple[str, str], ...],
    baseline: tuple[tuple[str, str], ...] | None,
    captcha_visible: bool,
    saw_captcha: bool,
    grace_elapsed: bool,
    login_ui_visible: bool = False,
) -> bool:
    if login_ui_visible:
        return False
    if not has_session:
        return False
    if reason == "captcha":
        if captcha_visible:
            return False
        return saw_captcha or grace_elapsed
    if baseline is None:
        return False
    if not baseline:
        return True
    return fingerprint != baseline
