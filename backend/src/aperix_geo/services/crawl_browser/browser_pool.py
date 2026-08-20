"""Browser sessions for geo-web-crawl jobs.

Production: one Chrome/Chromium ``user-data-dir`` per account (same dir as noVNC login).
Local smoke without ``account_id``: ephemeral ``chromium.launch`` + ``storage_state``.

Headless is ``GEO_WEB_CRAWL_HEADLESS`` only (not a per-job payload field).
Prefer system Google Chrome when present (fewer automation / SwiftShader fingerprints
than Playwright's bundled browser). Stealth flags drop the “controlled by automated
test software” banner and blunt ``navigator.webdriver``.
"""

from __future__ import annotations

import fcntl
import logging
import os
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator
from urllib.parse import unquote, urlparse

from aperix_geo.services.crawl_accounts.profiles import account_profile_dir, profile_is_ready

logger = logging.getLogger(__name__)

VIEWPORT = {"width": 1440, "height": 900}
# --no-sandbox is only added when required (root / Docker / explicit env).
# Pair with --test-type so Chrome does not show the yellow “unsupported flag” bar.
_BASE_ARGS = ["--disable-dev-shm-usage", "--disable-quic"]
# Do NOT put --disable-gpu on headed/Xvfb: software compositing + x11vnc looks like
# constant page flicker. Headless still disables GPU below.
_HEADED_EXTRA_ARGS = [
    "--window-size=1440,900",
]
_HEADLESS_EXTRA_ARGS = [
    "--disable-gpu",
]
# Blunt common automation signals (Doubao / similar risk engines).
_STEALTH_ARGS = [
    "--disable-blink-features=AutomationControlled",
]
_IGNORE_DEFAULT_ARGS = ["--enable-automation"]
_WEBDRIVER_INIT_SCRIPT = """
Object.defineProperty(navigator, 'webdriver', {
  get: () => undefined,
});
"""

# Prefer Google Chrome; fall back to Debian Chromium.
_CHROME_CANDIDATES = (
    "/usr/bin/google-chrome-stable",
    "/usr/bin/google-chrome",
    "/usr/bin/chromium",
    "/usr/bin/chromium-browser",
)

# HTTP CONNECT does not carry QUIC/STUN/IPv6. Captcha sprites then fail with
# 「图片加载失败，请刷新重试或换个网络」 even though the chat page loaded.
_PROXY_LOCKDOWN_ARGS = [
    "--disable-quic",
    "--force-webrtc-ip-handling-policy=disable_non_proxied_udp",
    "--webrtc-ip-handling-policy=disable_non_proxied_udp",
    "--disable-ipv6",
]


def _proxy_env_url() -> str:
    return (
        os.environ.get("HTTPS_PROXY")
        or os.environ.get("HTTP_PROXY")
        or os.environ.get("https_proxy")
        or os.environ.get("http_proxy")
        or ""
    ).strip()


def _playwright_proxy() -> dict[str, str] | None:
    """Playwright ``proxy=`` (Chromium ignores HTTP_PROXY; --proxy-server skips auth)."""
    raw = _proxy_env_url()
    if not raw:
        return None
    parsed = urlparse(raw if "://" in raw else f"http://{raw}")
    host = parsed.hostname
    if not host:
        logger.warning("geo-web-crawl proxy URL has no host; ignored")
        return None
    scheme = (parsed.scheme or "http").lower()
    port = parsed.port
    if scheme in {"socks5", "socks5h"}:
        server = f"socks5://{host}:{port or 1080}"
    elif scheme == "socks4":
        server = f"socks4://{host}:{port or 1080}"
    else:
        server = f"http://{host}:{port or 8080}"
    cfg: dict[str, str] = {"server": server}
    if parsed.username:
        cfg["username"] = unquote(parsed.username)
    if parsed.password:
        cfg["password"] = unquote(parsed.password)
    bypass = (os.environ.get("NO_PROXY") or os.environ.get("no_proxy") or "").strip()
    if bypass:
        cfg["bypass"] = bypass
    logger.info("geo-web-crawl chromium proxy=%s", server)
    return cfg


def _truthy_env(name: str, default: str = "") -> bool:
    raw = (os.environ.get(name) or default).strip().lower()
    return raw in {"1", "true", "yes", "on"}


def stealth_enabled() -> bool:
    """Drop automation banner / blunt webdriver (default on; set GEO_WEB_CRAWL_STEALTH=0 to disable)."""
    return _truthy_env("GEO_WEB_CRAWL_STEALTH", "true")


def _need_no_sandbox() -> bool:
    """Chrome sandbox needs user namespaces; root/Docker usually cannot use it.

    Override: ``GEO_WEB_CRAWL_NO_SANDBOX=1|0``. Empty → auto (root or ``/.dockerenv``).
    """
    raw = (os.environ.get("GEO_WEB_CRAWL_NO_SANDBOX") or "").strip().lower()
    if raw in {"1", "true", "yes", "on"}:
        return True
    if raw in {"0", "false", "no", "off"}:
        return False
    if Path("/.dockerenv").exists():
        return True
    try:
        return os.geteuid() == 0
    except AttributeError:
        return False


def _chromium_launch_kwargs(*, want_headless: bool) -> dict[str, Any]:
    args = list(_BASE_ARGS)
    if _need_no_sandbox():
        args.extend(["--no-sandbox", "--test-type"])
    if want_headless:
        args.extend(_HEADLESS_EXTRA_ARGS)
    else:
        args.extend(_HEADED_EXTRA_ARGS)
    if stealth_enabled():
        for flag in _STEALTH_ARGS:
            if flag not in args:
                args.append(flag)
    proxy = _playwright_proxy()
    if proxy:
        for flag in _PROXY_LOCKDOWN_ARGS:
            if flag not in args:
                args.append(flag)
    kwargs: dict[str, Any] = {
        "headless": want_headless,
        "args": args,
    }
    if stealth_enabled():
        kwargs["ignore_default_args"] = list(_IGNORE_DEFAULT_ARGS)
    if proxy:
        kwargs["proxy"] = proxy
    chrome = chrome_executable()
    if chrome:
        kwargs["executable_path"] = chrome
    return kwargs


_occupancy_lock = threading.Lock()
_occupancy: dict[str, str] = {}


class AccountBusy(RuntimeError):
    """This account's Chrome profile is already held by a job or login session."""


def _headless() -> bool:
    if vnc_enabled():
        return False
    raw = (os.environ.get("GEO_WEB_CRAWL_HEADLESS") or "true").strip().lower()
    return raw not in {"0", "false", "no", "off"}


def vnc_enabled() -> bool:
    return _truthy_env("GEO_WEB_CRAWL_VNC", "false")


def _env_port(name: str, default: int) -> int:
    raw = (os.environ.get(name) or "").strip()
    if not raw:
        return default
    try:
        port = int(raw)
    except ValueError:
        return default
    if 1 <= port <= 65535:
        return port
    return default


def novnc_listen_port() -> int:
    """websockify bind inside this container (default 6080)."""
    return _env_port("GEO_WEB_CRAWL_NOVNC_PORT", 6080)


def novnc_public_port() -> int:
    """Host / nginx port advertised to backend for ``{port}`` in the noVNC URL.

    Multi-container: map ``PUBLIC:LISTEN`` (e.g. ``6081:6080``) and set
    ``GEO_WEB_CRAWL_NOVNC_PUBLIC_PORT`` to the host side.
    """
    return _env_port("GEO_WEB_CRAWL_NOVNC_PUBLIC_PORT", novnc_listen_port())


def chrome_executable() -> str | None:
    """Resolve system Chrome/Chromium binary for Playwright ``executable_path``.

    Order: ``GEO_WEB_CRAWL_CHROME_BIN`` (if set) → Google Chrome → Chromium.
    """
    explicit = (os.environ.get("GEO_WEB_CRAWL_CHROME_BIN") or "").strip()
    candidates = (explicit,) if explicit else _CHROME_CANDIDATES
    for path in candidates:
        if path and Path(path).exists():
            return path
    if explicit:
        logger.warning("GEO_WEB_CRAWL_CHROME_BIN=%s missing; trying defaults", explicit)
        for path in _CHROME_CANDIDATES:
            if Path(path).exists():
                return path
    return None


def clear_chrome_singleton_locks(profile_dir: Path) -> None:
    """Stale SingletonLock from a killed Chrome leaves a black Xvfb."""
    for name in ("SingletonLock", "SingletonCookie", "SingletonSocket"):
        path = profile_dir / name
        try:
            if path.is_symlink() or path.exists():
                path.unlink()
                logger.info("geo-web-crawl removed leftover %s dir=%s", name, profile_dir)
        except OSError as exc:
            logger.warning("geo-web-crawl could not remove %s: %s", name, exc)


def account_occupancy(account_id: str) -> str:
    aid = (account_id or "").strip()
    if not aid:
        return ""
    with _occupancy_lock:
        return _occupancy.get(aid, "")


@contextmanager
def occupy_account(account_id: str, role: str) -> Iterator[None]:
    aid = (account_id or "").strip()
    if not aid:
        yield
        return
    with _occupancy_lock:
        current = _occupancy.get(aid)
        if current:
            raise AccountBusy(f"account {aid} busy ({current})")
        _occupancy[aid] = role
    try:
        yield
    finally:
        with _occupancy_lock:
            if _occupancy.get(aid) == role:
                del _occupancy[aid]


def browser_backend() -> str:
    return "profile" if (os.environ.get("GEO_CRAWL_PROFILE_ROOT") or "").strip() else "local"


def prepare_sync_playwright_runtime() -> None:
    """Clear a leftover asyncio loop so Sync Playwright can start."""
    import asyncio

    try:
        try:
            asyncio.get_running_loop()
            logger.warning("geo-web-crawl: asyncio loop already running; Sync Playwright may fail")
            return
        except RuntimeError:
            pass
        asyncio.set_event_loop(None)
    except Exception:
        logger.debug("prepare_sync_playwright_runtime failed", exc_info=True)


def parse_job_session(payload: dict[str, Any]) -> tuple[str, dict[str, Any], str]:
    """Return ``(account_id, storage_state, platform)``.

    Production (``GEO_CRAWL_PROFILE_ROOT`` set) requires ``account_id``.
    Local smoke without a profile root requires ``storage_state``.
    """
    platform = str(payload.get("platform") or "doubao").strip().lower() or "doubao"
    account_id = str(payload.get("account_id") or "").strip()
    storage_state = payload.get("storage_state")
    if (os.environ.get("GEO_CRAWL_PROFILE_ROOT") or "").strip() and not account_id:
        raise ValueError("account_id required when GEO_CRAWL_PROFILE_ROOT is set")
    if not account_id and not isinstance(storage_state, dict):
        raise ValueError("storage_state missing")
    if not isinstance(storage_state, dict):
        storage_state = {"cookies": []}
    return account_id, storage_state, platform


def apply_browser_context_defaults(context: Any, *, timeout_ms: int) -> None:
    context.set_default_timeout(max(1_000, int(timeout_ms)))
    perms = ["clipboard-read", "clipboard-write"]
    try:
        context.grant_permissions(perms)
    except Exception:
        logger.debug("clipboard permission grant skipped", exc_info=True)
    for origin in ("https://www.doubao.com", "https://doubao.com"):
        try:
            context.grant_permissions(perms, origin=origin)
        except Exception:
            logger.debug("clipboard permission grant skipped origin=%s", origin, exc_info=True)
    if stealth_enabled():
        try:
            context.add_init_script(_WEBDRIVER_INIT_SCRIPT)
        except Exception:
            logger.debug("webdriver init script skipped", exc_info=True)


# Back-compat alias.
_apply_context_defaults = apply_browser_context_defaults


@contextmanager
def _profile_lock(profile_dir: Path) -> Iterator[None]:
    profile_dir.mkdir(parents=True, exist_ok=True)
    fh = (profile_dir / ".aperix.lock").open("a+")
    try:
        fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
        yield
    finally:
        try:
            fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
        except OSError:
            pass
        fh.close()


def _start_playwright():
    from playwright.sync_api import sync_playwright

    prepare_sync_playwright_runtime()
    pw_cm = sync_playwright()
    return pw_cm, pw_cm.start()


def _stop_playwright(pw_cm: Any) -> None:
    try:
        pw_cm.__exit__(None, None, None)
    except Exception:
        logger.debug("playwright exit failed", exc_info=True)


def persistent_launch_kwargs(*, want_headless: bool) -> dict[str, Any]:
    kwargs = _chromium_launch_kwargs(want_headless=want_headless)
    kwargs["locale"] = "zh-CN"
    kwargs["viewport"] = VIEWPORT
    return kwargs


@contextmanager
def _page_session_profile(
    *,
    profile_dir: Path,
    timeout_ms: int,
    account_id: str = "",
) -> Iterator[tuple[Any, Any]]:
    want_headless = _headless()
    chrome = chrome_executable()
    logger.info(
        "geo-web-crawl persistent profile dir=%s headless=%s vnc=%s chrome=%s stealth=%s thread=%s",
        profile_dir,
        want_headless,
        vnc_enabled(),
        chrome or "playwright-bundled",
        stealth_enabled(),
        threading.current_thread().name,
    )
    pw_cm, playwright = _start_playwright()
    context = None
    try:
        with occupy_account(account_id, "job"):
            with _profile_lock(profile_dir):
                if not want_headless:
                    clear_chrome_singleton_locks(profile_dir)
                context = playwright.chromium.launch_persistent_context(
                    str(profile_dir),
                    **persistent_launch_kwargs(want_headless=want_headless),
                )
                apply_browser_context_defaults(context, timeout_ms=timeout_ms)
                page = context.pages[0] if context.pages else context.new_page()
                yield page, context
    finally:
        if context is not None:
            try:
                context.close()
            except Exception:
                logger.debug("persistent context close failed", exc_info=True)
        _stop_playwright(pw_cm)


@contextmanager
def _page_session_ephemeral(
    *,
    storage_state: dict[str, Any],
    timeout_ms: int,
) -> Iterator[tuple[Any, Any]]:
    """Local smoke only: a fresh Chrome with Playwright storage_state (not production)."""
    want_headless = _headless()
    logger.info(
        "geo-web-crawl ephemeral chrome headless=%s stealth=%s chrome=%s (no account profile)",
        want_headless,
        stealth_enabled(),
        chrome_executable() or "playwright-bundled",
    )
    pw_cm, playwright = _start_playwright()
    browser = None
    context = None
    try:
        launch_kw = _chromium_launch_kwargs(want_headless=want_headless)
        browser = playwright.chromium.launch(**launch_kw)
        context = browser.new_context(
            storage_state=storage_state or {"cookies": []},
            locale="zh-CN",
            viewport=VIEWPORT,
        )
        apply_browser_context_defaults(context, timeout_ms=timeout_ms)
        yield context.new_page(), context
    finally:
        if context is not None:
            try:
                context.close()
            except Exception:
                logger.debug("ephemeral context close failed", exc_info=True)
        if browser is not None:
            try:
                browser.close()
            except Exception:
                logger.debug("ephemeral browser close failed", exc_info=True)
        _stop_playwright(pw_cm)


@contextmanager
def page_session(
    *,
    storage_state: dict[str, Any],
    timeout_ms: int,
    account_id: str = "",
    platform: str = "doubao",
) -> Iterator[tuple[Any, Any]]:
    aid = (account_id or "").strip()
    if (os.environ.get("GEO_CRAWL_PROFILE_ROOT") or "").strip() and not aid:
        raise RuntimeError("account_id required when GEO_CRAWL_PROFILE_ROOT is set")
    if aid:
        profile_dir = account_profile_dir(platform, aid)
        if not profile_is_ready(profile_dir):
            raise RuntimeError(
                f"chrome profile missing for account={aid} dir={profile_dir}; "
                "complete noVNC login first"
            )
        with _page_session_profile(
            profile_dir=profile_dir,
            timeout_ms=timeout_ms,
            account_id=aid,
        ) as pair:
            yield pair
        return
    with _page_session_ephemeral(
        storage_state=storage_state,
        timeout_ms=timeout_ms,
    ) as pair:
        yield pair
