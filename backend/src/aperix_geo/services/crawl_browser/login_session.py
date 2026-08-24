"""In-process noVNC login sessions inside geo-web-crawl.

Same Chromium profile as jobs. Completing a ticket closes this Chrome;
Xvfb / noVNC stay up.
"""

from __future__ import annotations

import json
import logging
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from aperix_geo.services.crawl_accounts.platforms import (
    normalize_login_reason,
    normalize_platform,
    platform_start_url,
)
from aperix_geo.services.crawl_accounts.profiles import account_profile_dir
from aperix_geo.services.crawl_browser.browser_pool import (
    AccountBusy,
    account_occupancy,
    apply_browser_context_defaults,
    chrome_executable,
    clear_chrome_singleton_locks,
    novnc_public_port,
    occupy_account,
    persistent_launch_kwargs,
    prepare_sync_playwright_runtime,
    vnc_enabled,
)
from aperix_geo.services.crawl_browser.login_watch import (
    baseline_fingerprint,
    login_proof_cookie_names,
    page_chat_session_ready,
    page_has_captcha,
    page_shows_login_ui,
    ready_for_complete,
    session_fingerprint,
)

logger = logging.getLogger(__name__)

LOGIN_SESSION_PREFIX = "crawl-login:"

_lock = threading.Lock()
_sessions: dict[str, "_LoginSession"] = {}


class LoginSessionError(RuntimeError):
    """Cannot start or stop a crawl login session."""


@dataclass
class LoginSessionInfo:
    account_id: str
    session_id: str
    watching: bool
    platform: str
    reason: str


def session_id_for_account(account_id: str) -> str:
    aid = (account_id or "").strip()
    return f"{LOGIN_SESSION_PREFIX}{aid}"


def parse_login_session_id(raw: str) -> str:
    """Return account_id if this is a crawl-login session id, else empty."""
    text = (raw or "").strip()
    if text.startswith(LOGIN_SESSION_PREFIX):
        return text[len(LOGIN_SESSION_PREFIX) :].strip()
    return ""


def login_session_status(account_id: str) -> LoginSessionInfo | None:
    aid = (account_id or "").strip()
    with _lock:
        sess = _sessions.get(aid)
        if sess is None:
            return None
        return LoginSessionInfo(
            account_id=aid,
            session_id=session_id_for_account(aid),
            watching=sess.thread.is_alive() and not sess.stop.is_set(),
            platform=sess.platform,
            reason=sess.reason,
        )


def login_session_running(account_id: str) -> bool:
    info = login_session_status(account_id)
    return bool(info and info.watching)


class _LoginSession:
    def __init__(
        self,
        *,
        account_id: str,
        platform: str,
        reason: str,
        start_url: str,
        ticket_token: str,
        complete_url: str,
        ttl_min: int,
        captcha_clear_stable_s: float,
        baseline_state: dict[str, Any] | None,
        profile_dir: Path,
    ) -> None:
        self.account_id = account_id
        self.platform = platform
        self.reason = reason
        self.start_url = start_url
        self.ticket_token = ticket_token
        self.complete_url = complete_url
        self.ttl_min = ttl_min
        self.captcha_clear_stable_s = captcha_clear_stable_s
        self.baseline_state = baseline_state
        self.profile_dir = profile_dir
        self.stop = threading.Event()
        self.thread = threading.Thread(
            target=self._run,
            name=f"crawl-login-{account_id[:8]}",
            daemon=True,
        )

    def _run(self) -> None:
        try:
            with occupy_account(self.account_id, "login"):
                _watch_login(self)
        except AccountBusy as exc:
            logger.warning("geo-web-crawl login skipped: %s", exc)
        except Exception:
            logger.exception(
                "geo-web-crawl login session failed account=%s", self.account_id
            )
        finally:
            with _lock:
                current = _sessions.get(self.account_id)
                if current is self:
                    _sessions.pop(self.account_id, None)


def start_login_session(
    *,
    account_id: str,
    platform: str,
    start_url: str,
    ticket_token: str,
    complete_url: str,
    ttl_min: int,
    reason: str = "login_expired",
    captcha_clear_stable_s: float = 10.0,
    baseline_storage_state: dict[str, Any] | None = None,
) -> LoginSessionInfo:
    aid = (account_id or "").strip()
    if not aid:
        raise LoginSessionError("account_id required")
    plat = normalize_platform(platform)
    ops_reason = normalize_login_reason(reason)
    token = (ticket_token or "").strip()
    if not token:
        raise LoginSessionError("ticket_token required")

    with _lock:
        existing = _sessions.get(aid)
    if existing is not None and existing.thread.is_alive():
        logger.warning("geo-web-crawl replacing login session account=%s", aid)
        stop_login_session(aid)

    busy = account_occupancy(aid)
    if busy:
        raise LoginSessionError(f"account {aid} busy ({busy})")

    try:
        profile_dir = account_profile_dir(plat, aid)
    except ValueError as exc:
        raise LoginSessionError(str(exc)) from exc
    profile_dir.mkdir(parents=True, exist_ok=True)

    with _lock:
        sess = _LoginSession(
            account_id=aid,
            platform=plat,
            reason=ops_reason,
            start_url=(start_url or "").strip() or platform_start_url(plat),
            ticket_token=token,
            complete_url=(complete_url or "").strip(),
            ttl_min=max(5, int(ttl_min)),
            captcha_clear_stable_s=max(5.0, min(600.0, float(captcha_clear_stable_s))),
            baseline_state=baseline_storage_state
            if isinstance(baseline_storage_state, dict)
            else None,
            profile_dir=profile_dir,
        )
        _sessions[aid] = sess
        sess.thread.start()
        logger.info(
            "geo-web-crawl login started account=%s reason=%s vnc=%s display headed=%s",
            aid,
            ops_reason,
            novnc_public_port() if vnc_enabled() else "-",
            True,
        )
        return LoginSessionInfo(
            account_id=aid,
            session_id=session_id_for_account(aid),
            watching=True,
            platform=plat,
            reason=ops_reason,
        )


def stop_login_session(account_id: str, *, timeout_s: float = 45.0) -> bool:
    """Ask the login watcher to exit and close Chromium (desktop stays up)."""
    aid = (account_id or "").strip()
    if not aid:
        return False
    with _lock:
        sess = _sessions.get(aid)
    if sess is None:
        return False
    sess.stop.set()
    sess.thread.join(timeout=max(1.0, float(timeout_s)))
    return not sess.thread.is_alive()


def _post_complete(url: str, token: str, state: dict[str, Any]) -> None:
    body = json.dumps({"token": token, "storage_state": state}, ensure_ascii=False).encode(
        "utf-8"
    )
    req = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
        if resp.status >= 400:
            raise RuntimeError(f"complete HTTP {resp.status}: {raw[:500]}")


def _complete_url_hint(url: str) -> str:
    try:
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
    except Exception:
        return url[:120]


def _watch_login(sess: _LoginSession) -> None:
    from playwright.sync_api import sync_playwright

    prepare_sync_playwright_runtime()
    clear_chrome_singleton_locks(sess.profile_dir)
    chrome = chrome_executable()
    deadline = time.monotonic() + sess.ttl_min * 60
    login_baseline = baseline_fingerprint(sess.platform, sess.baseline_state)
    captcha_clear_stable_s = float(sess.captcha_clear_stable_s)
    logger.info(
        "geo-web-crawl login watch account=%s dir=%s chrome=%s complete=%s "
        "baseline=%s captcha_clear_stable_s=%s",
        sess.account_id,
        sess.profile_dir,
        chrome or "playwright",
        _complete_url_hint(sess.complete_url) or "-",
        len(login_baseline),
        captcha_clear_stable_s,
    )

    pw_cm = sync_playwright()
    playwright = pw_cm.start()
    context = None
    try:
        launch_kw = persistent_launch_kwargs(want_headless=False)
        context = playwright.chromium.launch_persistent_context(
            str(sess.profile_dir),
            **launch_kw,
        )
        apply_browser_context_defaults(context, timeout_ms=120_000)
        page = context.pages[0] if context.pages else context.new_page()
        try:
            page.goto(sess.start_url, wait_until="domcontentloaded", timeout=120_000)
        except Exception as exc:  # noqa: BLE001
            logger.warning("geo-web-crawl login goto warning: %s", exc)

        if not sess.complete_url:
            logger.warning("geo-web-crawl login has no complete_url; wait for TTL/stop")
            while not sess.stop.is_set() and time.monotonic() < deadline:
                time.sleep(1.0)
            return

        stable_hit = 0
        saw_captcha = False
        captcha_gone_since: float | None = None
        last_heartbeat = 0.0
        poll_i = 0
        while not sess.stop.is_set() and time.monotonic() < deadline:
            try:
                state = context.storage_state()
            except Exception as exc:  # noqa: BLE001
                logger.warning("geo-web-crawl login storage_state: %s", exc)
                time.sleep(2.0)
                continue
            if not isinstance(state, dict):
                state = {"cookies": []}
            proof_names = login_proof_cookie_names(sess.platform, state)
            fp = session_fingerprint(sess.platform, state)
            has_session = bool(proof_names)
            pages = list(context.pages)
            page = pages[0] if pages else None
            captcha_visible = page_has_captcha(page) if page is not None else False
            login_ui_visible = page_shows_login_ui(page)
            chat_ready = page_chat_session_ready(page)
            now = time.monotonic()
            if captcha_visible:
                saw_captcha = True
                captcha_gone_since = None
            elif saw_captcha and captcha_gone_since is None:
                captcha_gone_since = now
            captcha_clear_stable = bool(
                saw_captcha
                and not captcha_visible
                and captcha_gone_since is not None
                and (now - captcha_gone_since) >= captcha_clear_stable_s
            )
            poll_i += 1
            if now - last_heartbeat >= 30.0:
                last_heartbeat = now
                cookie_n = len(state.get("cookies") or [])
                logger.info(
                    "geo-web-crawl login heartbeat poll=%s cookies=%s proof=%s "
                    "chat_ready=%s login_ui=%s captcha=%s clear_stable=%s",
                    poll_i,
                    cookie_n,
                    ",".join(proof_names) or "-",
                    chat_ready,
                    login_ui_visible,
                    captcha_visible,
                    captcha_clear_stable,
                )
            baseline = login_baseline if sess.reason == "login_expired" else None
            ok = ready_for_complete(
                reason=sess.reason,
                has_session=has_session,
                fingerprint=fp,
                baseline=baseline,
                captcha_visible=captcha_visible,
                saw_captcha=saw_captcha,
                grace_elapsed=False,
                login_ui_visible=login_ui_visible,
                captcha_clear_stable=captcha_clear_stable,
                chat_session_ready=chat_ready,
            )
            if ok:
                stable_hit += 1
                logger.info(
                    "geo-web-crawl login ready proof=%s chat_ready=%s stable=%s/2",
                    ",".join(proof_names) or "-",
                    chat_ready,
                    stable_hit,
                )
                if stable_hit >= 2:
                    try:
                        _post_complete(sess.complete_url, sess.ticket_token, state)
                    except (
                        urllib.error.URLError,
                        urllib.error.HTTPError,
                        RuntimeError,
                        OSError,
                    ) as exc:
                        logger.warning("geo-web-crawl login complete failed: %s", exc)
                        stable_hit = 0
                        time.sleep(5.0)
                        continue
                    logger.info("geo-web-crawl login ticket completed account=%s", sess.account_id)
                    return
            else:
                stable_hit = 0
            # Captcha watch: lighter poll (DOM text scans); avoid tight loops looking like flicker.
            time.sleep(5.0 if sess.reason == "captcha" else 3.0)
        logger.info(
            "geo-web-crawl login ended account=%s stop=%s ttl=%s",
            sess.account_id,
            sess.stop.is_set(),
            time.monotonic() >= deadline,
        )
    finally:
        if context is not None:
            try:
                context.close()
            except Exception:
                logger.debug("geo-web-crawl login context close failed", exc_info=True)
        try:
            pw_cm.__exit__(None, None, None)
        except Exception:
            logger.debug("geo-web-crawl login playwright exit failed", exc_info=True)
