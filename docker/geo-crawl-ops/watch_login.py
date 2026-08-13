#!/usr/bin/env python3
"""Watch Chromium (CDP) and POST storage_state when human ops is done.

Env:
  GEO_CRAWL_OPS_PLATFORM       doubao | …
  GEO_CRAWL_OPS_REASON         login_expired | captcha
  GEO_CRAWL_OPS_TICKET_TOKEN   pending ticket token
  GEO_CRAWL_OPS_COMPLETE_URL   POST JSON {token, storage_state}
  GEO_CRAWL_OPS_CDP_URL        default http://127.0.0.1:9222
  GEO_CRAWL_OPS_TTL_MIN        stop watching after this many minutes
  GEO_CRAWL_OPS_STORAGE_STATE_PATH  optional inject file — used as login_expired baseline

Complete rules:
  login_expired — session cookies present AND fingerprint != baseline
                  baseline = fingerprint(injected storage_state) if any session cookies
                  there, else () (any new session completes).
                  Do NOT snapshot live cookies after a long settle — that races human
                  login and freezes baseline on the post-login cookies.
  captcha       — session cookies present AND captcha UI gone for 2 polls;
                  prefers having seen captcha once; else waits grace window
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

DONE_FLAG = "/tmp/ops-done"
LIVE_STATE_PATH = Path(
    (os.environ.get("GEO_CRAWL_OPS_LIVE_STATE_PATH") or "/tmp/ops-live-storage-state.json").strip()
)

_DOUBAO_SESSION = frozenset(
    {
        "sessionid",
        "sessionid_ss",
        "sid_guard",
        "sid_tt",
        "uid_tt",
        "uid_tt_ss",
    }
)

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


def _log(msg: str) -> None:
    print(f"[geo-crawl-ops-watch] {msg}", flush=True)


def session_cookie_names(platform: str, state: dict[str, Any]) -> list[str]:
    cookies = state.get("cookies") or []
    wanted = _DOUBAO_SESSION if platform == "doubao" else None
    found: list[str] = []
    for cookie in cookies:
        if not isinstance(cookie, dict):
            continue
        name = str(cookie.get("name") or "")
        value = str(cookie.get("value") or "").strip()
        if not value:
            continue
        if wanted is not None:
            if name in wanted:
                found.append(name)
        elif name.startswith("session") or name.startswith("sid_"):
            found.append(name)
    return sorted(set(found))


def session_fingerprint(platform: str, state: dict[str, Any]) -> tuple[tuple[str, str], ...]:
    """Stable (name, value) pairs for session cookies — used to detect re-login."""
    cookies = state.get("cookies") or []
    wanted = _DOUBAO_SESSION if platform == "doubao" else None
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
    return tuple(sorted(pairs))


def load_login_baseline(platform: str, state_path: str) -> tuple[tuple[str, str], ...]:
    """Baseline for login_expired: injected session cookies, or empty (= any session OK)."""
    path = (state_path or "").strip()
    if not path:
        return ()
    p = Path(path)
    if not p.is_file():
        return ()
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ()
    if not isinstance(raw, dict):
        return ()
    return session_fingerprint(platform, raw)


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


def _pick_page(browser: Any) -> Any | None:
    for context in browser.contexts:
        pages = list(context.pages)
        if pages:
            return pages[0]
    return None


def pick_best_context_state(
    browser: Any, platform: str
) -> tuple[Any | None, dict[str, Any], list[str], tuple[tuple[str, str], ...]]:
    """Prefer the CDP context that actually holds Doubao session cookies / pages.

    Playwright-launched Chromium often exposes an empty default context as
    ``contexts[0]``; the headed login window lives in another context. Reading
    only index 0 makes the watcher think login never happened.
    """
    best_ctx = None
    best_state: dict[str, Any] = {"cookies": []}
    best_names: list[str] = []
    best_fp: tuple[tuple[str, str], ...] = ()
    best_score = -1
    for context in browser.contexts:
        try:
            state = context.storage_state()
        except Exception:
            continue
        if not isinstance(state, dict):
            continue
        names = session_cookie_names(platform, state)
        fp = session_fingerprint(platform, state)
        cookies = state.get("cookies") if isinstance(state.get("cookies"), list) else []
        try:
            page_n = len(context.pages)
        except Exception:
            page_n = 0
        # Session cookies dominate; then total cookies; then open pages.
        score = len(names) * 1000 + len(cookies) * 10 + page_n
        if score > best_score:
            best_score = score
            best_ctx = context
            best_state = state
            best_names = names
            best_fp = fp
    return best_ctx, best_state, best_names, best_fp


def load_live_storage_state(platform: str) -> tuple[dict[str, Any] | None, list[str], tuple[tuple[str, str], ...]]:
    """Read storage_state dumped by launch_browser (authoritative cookie jar)."""
    if not LIVE_STATE_PATH.is_file():
        return None, [], ()
    try:
        raw = json.loads(LIVE_STATE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None, [], ()
    if not isinstance(raw, dict):
        return None, [], ()
    names = session_cookie_names(platform, raw)
    fp = session_fingerprint(platform, raw)
    return raw, names, fp


def resolve_storage_state(
    browser: Any, platform: str
) -> tuple[Any | None, dict[str, Any], list[str], tuple[tuple[str, str], ...], str]:
    """Prefer live dump from launch_browser; fall back to CDP contexts."""
    live, live_names, live_fp = load_live_storage_state(platform)
    ctx, cdp_state, cdp_names, cdp_fp = pick_best_context_state(browser, platform)
    if live is not None and (
        len(live_names) > len(cdp_names)
        or (
            len(live.get("cookies") or [])
            > len((cdp_state.get("cookies") if isinstance(cdp_state, dict) else None) or [])
        )
    ):
        return ctx, live, live_names, live_fp, "live"
    if live is not None and not cdp_names and live_names:
        return ctx, live, live_names, live_fp, "live"
    if live is not None and not cdp_names and not live_names:
        # Still prefer live jar when CDP is empty (even guest-only) so heartbeat is truthful.
        live_cookies = live.get("cookies") if isinstance(live.get("cookies"), list) else []
        cdp_cookies = cdp_state.get("cookies") if isinstance(cdp_state.get("cookies"), list) else []
        if len(live_cookies) >= len(cdp_cookies):
            return ctx, live, live_names, live_fp, "live"
    return ctx, cdp_state, cdp_names, cdp_fp, "cdp"


def _post_complete(url: str, token: str, state: dict[str, Any]) -> None:
    body = json.dumps({"token": token, "storage_state": state}, ensure_ascii=False).encode("utf-8")
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


def ready_for_complete(
    *,
    reason: str,
    has_session: bool,
    fingerprint: tuple[tuple[str, str], ...],
    baseline: tuple[tuple[str, str], ...] | None,
    captcha_visible: bool,
    saw_captcha: bool,
    grace_elapsed: bool,
) -> bool:
    if not has_session:
        return False
    if reason == "captcha":
        if captcha_visible:
            return False
        return saw_captcha or grace_elapsed
    # login_expired: need cookie change vs baseline (or any session if baseline empty)
    if baseline is None:
        return False
    if not baseline:
        return True
    return fingerprint != baseline


def _complete_url_hint(url: str) -> str:
    try:
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
    except Exception:
        return url[:120]


def main() -> int:
    platform = (os.environ.get("GEO_CRAWL_OPS_PLATFORM") or "web").strip().lower()
    reason = (os.environ.get("GEO_CRAWL_OPS_REASON") or "login_expired").strip().lower()
    if reason not in ("login_expired", "captcha"):
        reason = "login_expired"
    token = (os.environ.get("GEO_CRAWL_OPS_TICKET_TOKEN") or "").strip()
    complete_url = (os.environ.get("GEO_CRAWL_OPS_COMPLETE_URL") or "").strip()
    cdp = (os.environ.get("GEO_CRAWL_OPS_CDP_URL") or "http://127.0.0.1:9222").strip()
    ttl_min = int(os.environ.get("GEO_CRAWL_OPS_TTL_MIN") or "15")
    captcha_grace_s = float(os.environ.get("GEO_CRAWL_OPS_CAPTCHA_GRACE_S") or "20")
    state_path = (os.environ.get("GEO_CRAWL_OPS_STORAGE_STATE_PATH") or "").strip()

    if not token or not complete_url:
        _log("COMPLETE_URL or TICKET_TOKEN unset; watcher idle (manual upload still ok)")
        open(DONE_FLAG + ".skip", "w", encoding="utf-8").close()
        time.sleep(max(ttl_min, 1) * 60)
        return 0

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        _log("playwright not installed; cannot auto-export storage_state")
        return 1

    deadline = time.monotonic() + max(ttl_min, 1) * 60
    connected_at: float | None = None
    # Fixed baseline for login_expired (inject file or empty) — never race live login.
    login_baseline = load_login_baseline(platform, state_path)
    if reason == "login_expired":
        if login_baseline:
            _log(
                f"login baseline from inject cookies={len(login_baseline)} "
                f"(need change to complete)"
            )
        else:
            _log("login baseline empty (any session cookie completes)")
    stable_hit = 0
    saw_captcha = False
    last_heartbeat = 0.0
    poll_i = 0

    _log(
        f"watching reason={reason} platform={platform} cdp={cdp} "
        f"complete={_complete_url_hint(complete_url)}"
    )

    with sync_playwright() as playwright:
        browser = None
        while time.monotonic() < deadline:
            try:
                if browser is None or not browser.is_connected():
                    browser = playwright.chromium.connect_over_cdp(cdp)
                    if connected_at is None:
                        connected_at = time.monotonic()
                    stable_hit = 0
                    _log(f"cdp connected contexts={len(browser.contexts)}")

                contexts = browser.contexts
                if not contexts:
                    _log("cdp: no browser contexts yet")
                    time.sleep(2.0)
                    continue

                ctx, state, names, fp, state_src = resolve_storage_state(browser, platform)
                has_session = bool(names)
                poll_i += 1

                page = None
                if ctx is not None:
                    pages = list(ctx.pages)
                    page = pages[0] if pages else _pick_page(browser)
                else:
                    page = _pick_page(browser)
                captcha_visible = page_has_captcha(page) if page is not None else False
                if captcha_visible:
                    saw_captcha = True

                now = time.monotonic()
                if now - last_heartbeat >= 30.0:
                    last_heartbeat = now
                    cookie_n = len(state.get("cookies") or []) if isinstance(state, dict) else 0
                    _log(
                        f"heartbeat poll={poll_i} contexts={len(contexts)} "
                        f"src={state_src} cookies={cookie_n} "
                        f"session={','.join(names) or '-'} captcha={captcha_visible}"
                    )

                grace_elapsed = connected_at is not None and (now - connected_at) >= captcha_grace_s
                baseline = login_baseline if reason == "login_expired" else None
                ok = ready_for_complete(
                    reason=reason,
                    has_session=has_session,
                    fingerprint=fp,
                    baseline=baseline,
                    captcha_visible=captcha_visible,
                    saw_captcha=saw_captcha,
                    grace_elapsed=grace_elapsed,
                )

                if ok:
                    stable_hit += 1
                    _log(
                        f"ready names={','.join(names)} captcha={captcha_visible} "
                        f"saw_captcha={saw_captcha} stable={stable_hit}/2"
                    )
                    if stable_hit >= 2:
                        try:
                            _post_complete(complete_url, token, state)
                        except (urllib.error.URLError, urllib.error.HTTPError, RuntimeError, OSError) as exc:
                            _log(f"complete failed: {exc}; will retry")
                            stable_hit = 0
                            time.sleep(5.0)
                            continue
                        _log("ticket completed; writing done flag")
                        open(DONE_FLAG, "w", encoding="utf-8").close()
                        return 0
                else:
                    stable_hit = 0
                    if has_session or captcha_visible:
                        _log(
                            f"wait reason={reason} session={','.join(names) or '-'} "
                            f"captcha={captcha_visible} saw={saw_captcha} "
                            f"fp_changed={fp != login_baseline if reason == 'login_expired' else 'n/a'}"
                        )
            except Exception as exc:  # noqa: BLE001
                browser = None
                _log(f"cdp wait: {exc}")
            time.sleep(3.0)

    _log("ttl elapsed without complete")
    return 0


if __name__ == "__main__":
    sys.exit(main())
