"""Playwright storage_state cookie helpers for the crawl account pool.

Cookies in the DB are a side-channel (ticket complete / last_ok proof).
The live Doubao session lives in the per-account Chrome profile directory.
"""

from __future__ import annotations

import logging
from typing import Any

from aperix_geo.services.crawl_accounts.platforms import PLATFORM_DOUBAO, normalize_platform

logger = logging.getLogger(__name__)

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
_LOGIN_PROOF_COOKIE_NAMES: dict[str, frozenset[str]] = {
    PLATFORM_DOUBAO: frozenset({"sessionid", "sessionid_ss", "sid_guard"}),
}


def session_cookie_names_for_platform(platform: str) -> frozenset[str]:
    return _SESSION_COOKIE_NAMES.get(normalize_platform(platform), frozenset())


def login_proof_cookie_names_for_platform(platform: str) -> frozenset[str]:
    return _LOGIN_PROOF_COOKIE_NAMES.get(normalize_platform(platform), frozenset())


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


def job_payload_storage_state(payload: dict[str, Any]) -> dict[str, Any] | None:
    """Jar from the job payload. Profile jobs may omit it (Chrome already has the session)."""
    from aperix_geo.services.crawl_accounts.profiles import job_uses_account_profile

    state = payload.get("storage_state")
    if isinstance(state, dict):
        return state
    if job_uses_account_profile(payload):
        return {"cookies": []}
    return None


def job_requires_injected_session_cookies(payload: dict[str, Any]) -> bool:
    """Ephemeral Chrome (no account_id) still needs a session jar in the payload."""
    from aperix_geo.services.crawl_accounts.profiles import job_uses_account_profile

    return not job_uses_account_profile(payload)


def cookies_only_storage_state(state: dict[str, Any] | None) -> dict[str, Any]:
    """Keep Playwright cookies only; drop origins/localStorage (often MB-scale drafts)."""
    if not isinstance(state, dict):
        return {"cookies": []}
    cookies = state.get("cookies")
    if not isinstance(cookies, list):
        return {"cookies": []}
    kept: list[dict[str, Any]] = [c for c in cookies if isinstance(c, dict)]
    return {"cookies": kept}


def keep_session_storage_state(
    exported: dict[str, Any] | None,
    *,
    fallback: dict[str, Any] | None,
    platform: str = PLATFORM_DOUBAO,
    log_event: str = "cookie export",
) -> dict[str, Any]:
    """Prefer exported session cookies; if export is empty, keep fallback."""
    state = cookies_only_storage_state(exported)
    if storage_state_has_session_cookies(state, platform=platform):
        return state
    kept = cookies_only_storage_state(fallback)
    if storage_state_has_session_cookies(kept, platform=platform):
        logger.warning(
            "%s lost session cookies; keeping previous jar names=%s",
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
