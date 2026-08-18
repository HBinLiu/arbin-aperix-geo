"""Per-platform session-cookie helpers for crawl account pool / tickets / heartbeat."""

from __future__ import annotations

import logging
import time
from typing import Any

from aperix_geo.services.crawl_accounts.platforms import PLATFORM_DOUBAO, normalize_platform

logger = logging.getLogger(__name__)

_PLAYWRIGHT_COOKIE_KEYS = (
    "name",
    "value",
    "url",
    "domain",
    "path",
    "expires",
    "httpOnly",
    "secure",
    "sameSite",
)
_SAMESITE = frozenset({"Strict", "Lax", "None"})

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


def cookies_only_storage_state(state: dict[str, Any] | None) -> dict[str, Any]:
    """Keep Playwright cookies only; drop origins/localStorage (often MB-scale drafts)."""
    if not isinstance(state, dict):
        return {"cookies": []}
    cookies = state.get("cookies")
    if not isinstance(cookies, list):
        return {"cookies": []}
    kept: list[dict[str, Any]] = [c for c in cookies if isinstance(c, dict)]
    return {"cookies": kept}


def playwright_cookies_for_context(
    storage_state: dict[str, Any] | None,
    *,
    now: float | None = None,
) -> list[dict[str, Any]]:
    """Normalize cookies so Playwright / Browserless CDP actually applies them.

    Session cookies in storage_state use ``expires: -1`` (sometimes ``0``). Chrome
    CDP ``Network.setCookie`` treats those as already expired and drops them —
    heartbeat then sees a guest page and marks the account login_expired.
    """
    if not isinstance(storage_state, dict):
        return []
    cookies = storage_state.get("cookies")
    if not isinstance(cookies, list):
        return []
    now_ts = time.time() if now is None else float(now)
    out: list[dict[str, Any]] = []
    for raw in cookies:
        if not isinstance(raw, dict):
            continue
        name = str(raw.get("name") or "")
        value = str(raw.get("value") or "")
        if not name or not value.strip():
            continue
        cookie: dict[str, Any] = {}
        for key in _PLAYWRIGHT_COOKIE_KEYS:
            if key in raw:
                cookie[key] = raw[key]
        cookie["name"] = name
        cookie["value"] = value
        if not cookie.get("path"):
            cookie["path"] = "/"
        if not cookie.get("domain") and not cookie.get("url"):
            continue
        same_site = str(cookie.get("sameSite") or "")
        if same_site not in _SAMESITE:
            cookie["sameSite"] = "Lax"
        if cookie.get("sameSite") == "None":
            cookie["secure"] = True
        expires = cookie.get("expires")
        if expires is not None:
            try:
                exp = float(expires)
            except (TypeError, ValueError):
                cookie.pop("expires", None)
            else:
                if exp <= 0:
                    # Session cookie: omit so CDP does not treat -1/0 as expired.
                    cookie.pop("expires", None)
                elif exp < now_ts:
                    continue
                else:
                    cookie["expires"] = exp
        out.append(cookie)
    return out


def playwright_storage_state_for_context(
    storage_state: dict[str, Any] | None,
    *,
    now: float | None = None,
) -> dict[str, Any]:
    return {"cookies": playwright_cookies_for_context(storage_state, now=now)}


def keep_session_storage_state(
    exported: dict[str, Any] | None,
    *,
    fallback: dict[str, Any] | None,
    platform: str = PLATFORM_DOUBAO,
    log_event: str = "cookie export",
) -> dict[str, Any]:
    """Prefer exported session cookies; if CDP returns an empty jar, keep fallback."""
    state = cookies_only_storage_state(exported)
    if storage_state_has_session_cookies(state, platform=platform):
        return state
    kept = cookies_only_storage_state(fallback)
    if storage_state_has_session_cookies(kept, platform=platform):
        logger.warning(
            "%s lost session cookies; keeping injected jar names=%s",
            log_event,
            session_cookie_names(kept, platform=platform),
        )
        return kept
    return state


def storage_state_from_context(
    context: Any,
    *,
    fallback: dict[str, Any] | None,
    platform: str = PLATFORM_DOUBAO,
    log_event: str = "job",
) -> dict[str, Any]:
    exported = None
    if context is not None:
        try:
            exported = context.storage_state()
        except Exception as exc:  # noqa: BLE001
            logger.warning("%s storage_state export failed: %s", log_event, exc)
    return keep_session_storage_state(
        exported,
        fallback=fallback,
        platform=platform,
        log_event=log_event,
    )
