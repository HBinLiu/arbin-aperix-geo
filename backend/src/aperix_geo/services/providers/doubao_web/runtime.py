"""Doubao crawl runtime: modes, transport, job envelopes, page guards."""

from __future__ import annotations

import logging
import re
import time
from typing import Any, Literal, NoReturn

from aperix_geo.config import Settings
from aperix_geo.services.providers.doubao_web import selectors as sel
from aperix_geo.services.providers.doubao_web.errors import (
    DoubaoCaptchaRequired,
    DoubaoCrawlError,
    DoubaoLoginExpired,
    DoubaoNeedsHumanOps,
    DoubaoShareError,
)
from aperix_geo.services.providers.doubao_web.extract import page_looks_like_captcha

logger = logging.getLogger(__name__)

_SYSTEM_ERROR_RELOADS = 2
_STUCK_COMPOSER_RELOAD_S = 8.0

# --- modes ---

DOUBAO_JOB_MODES = frozenset({"crawl", "probe", "sign", "http", "share"})
DEFAULT_DOUBAO_JOB_MODE = "crawl"
# Legacy alias accepted by normalize_doubao_job_mode.
_DOUBAO_JOB_MODE_ALIASES = {"web_http": "http"}

CrawlTransport = Literal["ui", "hybrid"]
WebHttpVia = Literal["browser", "httpx"]

_HUMAN_OPS_TYPES = frozenset(
    {
        "DoubaoNeedsHumanOps",
        "DoubaoLoginExpired",
        "DoubaoCaptchaRequired",
    }
)


def normalize_doubao_job_mode(
    raw: str | None, *, default: str = DEFAULT_DOUBAO_JOB_MODE
) -> str:
    mode = (raw or default).strip().lower() or default
    mode = _DOUBAO_JOB_MODE_ALIASES.get(mode, mode)
    if mode not in DOUBAO_JOB_MODES:
        return default if default in DOUBAO_JOB_MODES else DEFAULT_DOUBAO_JOB_MODE
    return mode


def resolve_crawl_transport(settings: Settings) -> CrawlTransport:
    if not bool(settings.doubao_web_http_enabled):
        return "ui"
    raw = (settings.doubao_crawl_transport or "ui").strip().lower()
    return "hybrid" if raw == "hybrid" else "ui"


def resolve_web_http_via(settings: Settings) -> WebHttpVia:
    raw = (settings.doubao_web_http_via or "browser").strip().lower()
    return "httpx" if raw == "httpx" else "browser"


def chat_url_is_logged_out(url: str) -> bool:
    """True for passport / ``/login`` / ``from_logout`` — not a generic ``login`` substring."""
    lowered = (url or "").lower()
    return "passport" in lowered or "/login" in lowered or "from_logout" in lowered


# Accessible-name match for a real login / scan CTA (not 验证码 — that is captcha).
_LOGIN_CTA = re.compile(r"登录|登陆|扫码")


def spawn_doubao_job(
    payload: dict[str, Any],
    *,
    settings: Settings,
    mode: str,
    timeout_s: float | None = None,
) -> dict[str, Any]:
    """Run a Doubao crawl-browser job with settings-derived kwargs."""
    from aperix_geo.services.crawl_browser.client import run_crawl_job

    timeout = float(
        timeout_s
        if timeout_s is not None
        else payload.get("timeout_s")
        or settings.doubao_crawl_timeout_s
    )
    return run_crawl_job(
        payload,
        timeout_s=timeout,
        mode=mode,
        base_url=(settings.geo_web_crawl_base_url or "").strip(),
        token=(settings.geo_web_crawl_token or "").strip(),
    )


# --- job envelopes ---


def job_ok(**fields: Any) -> dict[str, Any]:
    storage_state = fields.pop("storage_state", None)
    out: dict[str, Any] = {
        "ok": True,
        "error_type": "",
        "error": "",
        "human_ops": False,
        "storage_state": storage_state,
    }
    out.update(fields)
    return out


def job_error(
    exc: BaseException,
    *,
    human_ops: bool | None = None,
    session_alive: bool | None = None,
    **empty_fields: Any,
) -> dict[str, Any]:
    if human_ops is None:
        human_ops = isinstance(exc, DoubaoNeedsHumanOps)
    if session_alive is None:
        session_alive = bool(getattr(exc, "session_alive", False))
    out: dict[str, Any] = {
        "ok": False,
        "error_type": type(exc).__name__,
        "error": str(exc),
        "human_ops": bool(human_ops),
        "session_alive": bool(session_alive),
        "storage_state": None,
    }
    out.update(empty_fields)
    return out


def raise_from_job(job: dict[str, Any]) -> NoReturn:
    err_type = str(job.get("error_type") or "DoubaoCrawlError")
    err_msg = str(job.get("error") or "job failed")
    session_alive = bool(job.get("session_alive"))
    if err_type == "DoubaoCaptchaRequired":
        raise DoubaoCaptchaRequired(err_msg)
    if err_type == "DoubaoLoginExpired":
        raise DoubaoLoginExpired(err_msg)
    if err_type == "DoubaoShareError":
        raise DoubaoShareError(err_msg)
    if job.get("human_ops") or err_type in _HUMAN_OPS_TYPES:
        raise DoubaoNeedsHumanOps(err_msg)
    raise DoubaoCrawlError(err_msg, session_alive=session_alive)


def is_human_ops_job(job: dict[str, Any]) -> bool:
    return bool(job.get("human_ops")) or str(job.get("error_type") or "") in _HUMAN_OPS_TYPES


# --- page guards ---


def _locator_is_visible(loc: Any) -> bool:
    try:
        vis = loc.is_visible()
    except Exception:
        return True
    return vis if isinstance(vis, bool) else True


def _composer(page: Any) -> Any | None:
    """Visible chat input only — hidden work-mode leftovers do not count."""
    try:
        for css in sel.COMPOSER_SELECTORS:
            loc = page.locator(css)
            n = min(int(loc.count()), 8)
            for i in range(n):
                el = loc.nth(i)
                if _locator_is_visible(el):
                    return el
        role = page.get_by_role("textbox")
        n = min(int(role.count()), 8)
        found = None
        for i in range(max(n, 0)):
            el = role.nth(i)
            if _locator_is_visible(el):
                found = el
        if found is not None:
            return found
    except Exception:
        return None
    return None


def page_has_system_error(page: Any) -> bool:
    try:
        body = page.locator("body").inner_text(timeout=1_500) or ""
    except Exception:
        return False
    return bool(sel.SYSTEM_ERROR_HINT.search(body))


def assert_no_system_error(page: Any) -> None:
    """Fail fast when Doubao shows「系统异常」toast (session usually still valid)."""
    if page_has_system_error(page):
        raise DoubaoCrawlError("doubao 系统异常", session_alive=True)


def recover_system_error(page: Any, *, base_url: str = "") -> bool:
    """Reload /chat when Doubao toasts「系统异常」(composer usually gone)."""
    if not page_has_system_error(page):
        return False
    target = (base_url or "").strip() or sel.CHAT_URL
    logger.warning("doubao 系统异常; reloading %s", target)
    try:
        page.goto(target, wait_until="domcontentloaded")
        page.wait_for_timeout(1_000)
    except Exception:
        logger.debug("goto after 系统异常 failed", exc_info=True)
        try:
            page.reload(wait_until="domcontentloaded")
            page.wait_for_timeout(1_000)
        except Exception:
            logger.debug("reload after 系统异常 failed", exc_info=True)
    return True


def _chat_tab(page: Any) -> Any:
    try:
        tab = page.get_by_role("button", name=sel.CHAT_TAB_NAME)
        if tab.count() > 0:
            return tab.first
    except Exception:
        pass
    try:
        labeled = page.locator("button").filter(has_text=sel.CHAT_TAB_NAME)
        if labeled.count() > 0:
            return labeled.first
    except Exception:
        pass
    return None


def _work_landing_visible(page: Any) -> bool:
    try:
        loc = page.get_by_text(sel.WORK_LANDING_HINT)
        n = min(int(loc.count()), 4)
        for i in range(n):
            if _locator_is_visible(loc.nth(i)):
                return True
    except Exception:
        return False
    return False


def _chat_tab_needs_click(page: Any) -> bool:
    if _work_landing_visible(page):
        return True
    tab = _chat_tab(page)
    if tab is None:
        return False
    try:
        pressed = (
            (tab.get_attribute("aria-pressed") or "")
            or (tab.get_attribute("aria-selected") or "")
        ).strip().lower()
        if pressed in ("true", "1"):
            return False
        if pressed in ("false", "0"):
            return True
    except Exception:
        pass
    try:
        cls = tab.get_attribute("class") or ""
    except Exception:
        cls = ""
    if "text-secondary" in cls:
        return True
    if "text-primary" in cls:
        return False
    return _composer(page) is None


def ensure_chat_mode(page: Any, *, wait_ms: int = 4_000) -> bool:
    """Click「对话」when landing is on「工作」. True if a click happened."""
    if wait_ms > 0:
        try:
            page.get_by_role("button", name=sel.WORK_TAB_NAME).first.wait_for(
                state="visible", timeout=wait_ms
            )
        except Exception:
            pass
    if not _chat_tab_needs_click(page):
        return False
    tab = _chat_tab(page)
    if tab is None:
        logger.warning("doubao work landing but 对话 button not found url=%s", page.url)
        return False
    try:
        tab.click(timeout=5_000)
        page.wait_for_timeout(600)
        logger.info("doubao switched to 对话 tab url=%s", page.url)
        return True
    except Exception:
        logger.debug("doubao 对话 tab click skipped", exc_info=True)
        return False


def wait_for_composer(
    page: Any, *, timeout_s: float = 12.0, base_url: str = ""
) -> Any:
    """Wait until the visible chat input exists; reload once on「系统异常」."""
    deadline = time.monotonic() + max(0.5, float(timeout_s))
    reloads = 0
    target = (base_url or "").strip() or sel.CHAT_URL
    while time.monotonic() < deadline:
        if recover_system_error(page, base_url=target):
            reloads += 1
            if reloads > _SYSTEM_ERROR_RELOADS:
                raise DoubaoCrawlError(
                    "chat composer not found (系统异常)", session_alive=True
                )
        try:
            ensure_chat_mode(page, wait_ms=0)
        except Exception:
            logger.debug("ensure_chat_mode while waiting composer failed", exc_info=True)
        box = _composer(page)
        if box is not None:
            return box
        page.wait_for_timeout(400)
    raise DoubaoCrawlError("chat composer not found", session_alive=True)


def _visible_login_reason(page: Any) -> str:
    """Guest-chrome evidence, or empty if none. Does not inspect the composer."""
    if chat_url_is_logged_out(page.url or ""):
        return f"redirected to login: {page.url}"

    for role in ("button", "link"):
        loc = page.get_by_role(role, name=_LOGIN_CTA)
        try:
            n = min(int(loc.count()), 12)
        except Exception:
            n = 0
        for i in range(n):
            try:
                el = loc.nth(i)
                if not el.is_visible():
                    continue
                label = ""
                try:
                    label = (el.inner_text(timeout=800) or "").strip()
                except Exception:
                    label = ""
                if _LOGIN_CTA.search(label):
                    return f"login UI visible ({role}={label or 'login'}); storage_state expired"
            except Exception:
                continue

    # Header「登录」often appears as plain text on guest shell (see end.png / body dump).
    try:
        login_text = page.get_by_text(re.compile(r"^\s*登录\s*$"))
        for i in range(min(login_text.count(), 8)):
            if login_text.nth(i).is_visible():
                return "login text visible; storage_state expired"
    except Exception:
        pass

    try:
        body = page.locator("body").inner_text(timeout=1_500) or ""
    except Exception:
        body = ""
    # Compact guest chrome: "…下载豆包电脑版 登录 有什么我能帮你的吗？"
    if re.search(r"(电脑版|关于豆包)\s*登录\s+", body) or re.search(
        r"\s登录\s+有什么我能帮你的吗", body
    ):
        return "guest shell copy with 登录; storage_state expired"
    return ""


def inspect_login(page: Any) -> tuple[str, str]:
    """``ok`` / ``out`` (logged out) / ``pending`` (SPA still hydrating)."""
    reason = _visible_login_reason(page)
    if reason:
        return "out", reason
    if _composer(page) is None:
        return "pending", "chat UI not ready (composer missing)"
    return "ok", ""


def wait_until_logged_in(
    page: Any, *, timeout_s: float = 20.0, base_url: str = ""
) -> None:
    """Wait for session hydrate after goto; fail immediately on passport / ``/login``.

    Guest chrome can flash「登录」on ``/chat/`` before cookies apply. A real
    redirect to passport is not a flash — raise without waiting.

    A slow blank shell (no composer, no login CTA) is **not** login expiry:
    timeout raises ``DoubaoCrawlError`` so heartbeat keeps the cookie jar.
    Work-mode landing has no chat input — switch to「对话」while waiting.
    「系统异常」toasts are reloaded, not treated as login expiry.
    """
    if chat_url_is_logged_out(page.url or ""):
        raise DoubaoLoginExpired(f"redirected to login: {page.url}")
    wait_load = getattr(page, "wait_for_load_state", None)
    if callable(wait_load):
        try:
            wait_load("load", timeout=min(8_000, int(max(0.5, float(timeout_s)) * 1000)))
        except Exception:
            pass
        if chat_url_is_logged_out(page.url or ""):
            raise DoubaoLoginExpired(f"redirected to login: {page.url}")
    deadline = time.monotonic() + max(0.5, float(timeout_s))
    started = time.monotonic()
    last: BaseException | None = None
    reloads = 0
    target = (base_url or "").strip() or sel.CHAT_URL
    while time.monotonic() < deadline:
        if chat_url_is_logged_out(page.url or ""):
            raise DoubaoLoginExpired(f"redirected to login: {page.url}")
        try:
            if recover_system_error(page, base_url=target):
                reloads += 1
                last = DoubaoCrawlError("doubao 系统异常", session_alive=True)
                if reloads > _SYSTEM_ERROR_RELOADS:
                    raise last
                continue
        except DoubaoCrawlError:
            raise
        except Exception:
            logger.debug("system-error recovery skipped", exc_info=True)
        try:
            ensure_chat_mode(page, wait_ms=0)
        except Exception:
            logger.debug("ensure_chat_mode during login wait failed", exc_info=True)
        try:
            assert_logged_in(page)
            return
        except DoubaoLoginExpired as exc:
            last = exc
            if chat_url_is_logged_out(page.url or ""):
                raise
        except DoubaoCrawlError as exc:
            last = exc
            stuck = time.monotonic() - started >= _STUCK_COMPOSER_RELOAD_S
            if reloads < _SYSTEM_ERROR_RELOADS and stuck and "composer" in str(exc).lower():
                logger.warning(
                    "composer still missing after %.0fs; reloading %s",
                    time.monotonic() - started,
                    target,
                )
                try:
                    page.goto(target, wait_until="domcontentloaded")
                    page.wait_for_timeout(800)
                    reloads += 1
                    started = time.monotonic()
                except Exception:
                    logger.debug("stuck-composer reload failed", exc_info=True)
        try:
            page.wait_for_timeout(400)
        except Exception as wait_exc:
            if last is not None:
                raise last from wait_exc
            raise
    if last is not None:
        raise last
    assert_logged_in(page)


def assert_logged_in(page: Any) -> None:
    """Raise when the chat UI is not an authenticated session.

    Guest landing often still shows a composer; a visible「登录」CTA or
    ``from_logout=1`` is login expiry. A missing composer on ``/chat/`` is
    treated as not-ready (``DoubaoCrawlError``), not a dead session.
    """
    state, reason = inspect_login(page)
    if state == "ok":
        return
    if state == "pending":
        raise DoubaoCrawlError(reason, session_alive=True)
    raise DoubaoLoginExpired(reason)


def page_has_captcha(page: Any) -> bool:
    try:
        body = page.locator("body").inner_text(timeout=2_000) or ""
    except Exception:
        body = ""
    if page_looks_like_captcha(body):
        return True
    for css in sel.CAPTCHA_DOM_SELECTORS:
        try:
            loc = page.locator(css)
            n = min(loc.count(), 5)
            for i in range(n):
                if loc.nth(i).is_visible():
                    return True
        except Exception:
            continue
    return False


def assert_no_captcha(page: Any) -> None:
    if page_has_captcha(page):
        raise DoubaoCaptchaRequired(
            "behavior captcha / 换个网络; account needs human ticket/alert recovery "
            "(no auto-solve; sampling may API-fallback; same proxy IP often cannot retry)"
        )
