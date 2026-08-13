"""Per-platform session-cookie helpers for crawl account pool / tickets / heartbeat."""

from __future__ import annotations

from typing import Any

from aperix_geo.services.crawl_accounts.platforms import PLATFORM_DOUBAO, normalize_platform

# Strong login signals per platform (guest cookies do not count).
_SESSION_COOKIE_NAMES: dict[str, frozenset[str]] = {
    PLATFORM_DOUBAO: frozenset(
        {
            "sessionid",
            "sessionid_ss",
            "sid_guard",
            "sid_tt",
            "uid_tt",
            "uid_tt_ss",
        }
    ),
}


def session_cookie_names_for_platform(platform: str) -> frozenset[str]:
    return _SESSION_COOKIE_NAMES.get(normalize_platform(platform), frozenset())


def session_cookie_names(
    storage_state: dict[str, Any] | None,
    *,
    platform: str = PLATFORM_DOUBAO,
) -> list[str]:
    names = session_cookie_names_for_platform(platform)
    if not names or not isinstance(storage_state, dict):
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
        if name in names and value:
            found.append(name)
    return sorted(set(found))


def storage_state_has_session_cookies(
    state: dict[str, Any] | None,
    *,
    platform: str = PLATFORM_DOUBAO,
) -> bool:
    return bool(session_cookie_names(state, platform=platform))


def storage_state_has_cookies(
    state: dict[str, Any] | None,
    *,
    platform: str = PLATFORM_DOUBAO,
) -> bool:
    """Alias: requires real session cookies, not guest-only jars."""
    return storage_state_has_session_cookies(state, platform=platform)
