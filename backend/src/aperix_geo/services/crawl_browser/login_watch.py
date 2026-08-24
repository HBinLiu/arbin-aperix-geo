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
from aperix_geo.services.providers.doubao_web.captcha import page_shows_behavior_captcha

# Exact header login CTA (avoid substring hits like「登录设备」).
_LOGIN_CTA = re.compile(r"^\s*登录\s*$")
_LOGGED_OUT_URL = re.compile(r"/passport|/login(?:/|\?|$)|from_logout=1", re.I)


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
                # Exact「登录」only — empty accessible-name must not count as logout.
                if label and re.search(r"^\s*登录\s*$", label):
                    return True
    except Exception:
        pass
    return False


def page_has_captcha(page: Any) -> bool:
    return page_shows_behavior_captcha(page)


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
    captcha_clear_stable: bool = False,
) -> bool:
    """Whether the noVNC watcher may POST ticket complete.

    ``login_expired``: session cookies + no login CTA/captcha is enough. Do **not**
    require cookie fingerprint to change — after behavior captcha the jar often
    stays the same, and requiring a change left tickets stuck → TTL reopen as
    login_expired spam while the profile was already logged in.

    ``captcha``: must have seen captcha, then clear + stable.
    """
    del grace_elapsed, fingerprint, baseline  # retained for call-site compat
    if login_ui_visible or captcha_visible:
        return False
    if not has_session:
        return False
    if reason == "captcha":
        # Never complete on grace alone: must have seen captcha, then clear + stable.
        if not saw_captcha:
            return False
        return captcha_clear_stable
    # login_expired (and unknown): already-authenticated profile can close the ticket.
    return True
