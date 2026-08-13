"""Doubao session-cookie helpers shared by pool / tickets / heartbeat / scripts.

Guest cookies such as ``odin_tt`` do **not** count as a logged-in session.
"""

from __future__ import annotations

from typing import Any

# Strong login signals (same set as scripts/doubao_web_login.py).
SESSION_COOKIE_NAMES = frozenset(
    {
        "sessionid",
        "sessionid_ss",
        "sid_guard",
        "sid_tt",
        "uid_tt",
        "uid_tt_ss",
    }
)


def session_cookie_names(storage_state: dict[str, Any] | None) -> list[str]:
    if not isinstance(storage_state, dict):
        return []
    cookies = storage_state.get("cookies")
    if not isinstance(cookies, list):
        return []
    found: list[str] = []
    for cookie in cookies:
        if not isinstance(cookie, dict):
            continue
        name = str(cookie.get("name") or "")
        value = str(cookie.get("value") or "").strip()
        if name in SESSION_COOKIE_NAMES and value:
            found.append(name)
    return sorted(set(found))


def storage_state_has_session_cookies(state: dict[str, Any] | None) -> bool:
    """True when Playwright state includes at least one Doubao session cookie."""
    return bool(session_cookie_names(state))


def storage_state_has_cookies(state: dict[str, Any] | None) -> bool:
    """Backward-compatible alias: requires real session cookies, not guest-only jars."""
    return storage_state_has_session_cookies(state)
