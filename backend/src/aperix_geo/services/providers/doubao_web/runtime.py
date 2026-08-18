"""Doubao crawl runtime: modes, transport, job envelopes, page guards."""

from __future__ import annotations

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
    """Run a Doubao geo-web-crawl job with settings-derived spawn kwargs."""
    from aperix_geo.services.geo_web_crawl.spawn import run_geo_web_crawl_spawn

    timeout = float(
        timeout_s
        if timeout_s is not None
        else payload.get("timeout_s")
        or settings.doubao_crawl_timeout_s
    )
    return run_geo_web_crawl_spawn(
        payload,
        timeout_s=timeout,
        docker_image=(settings.geo_web_crawl_docker_image or "").strip(),
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


def _composer(page: Any) -> Any | None:
    for css in sel.COMPOSER_SELECTORS:
        loc = page.locator(css)
        if loc.count() > 0:
            return loc.first
    role = page.get_by_role("textbox")
    if role.count() > 0:
        return role.last
    return None


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


def wait_until_logged_in(page: Any, *, timeout_s: float = 20.0) -> None:
    """Wait for session hydrate after goto; fail immediately on passport / ``/login``.

    Guest chrome can flash「登录」on ``/chat/`` before cookies apply. A real
    redirect to passport is not a flash — raise without waiting.

    A slow blank shell (no composer, no login CTA) is **not** login expiry:
    timeout raises ``DoubaoCrawlError`` so heartbeat keeps the cookie jar.
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
    last: BaseException | None = None
    while time.monotonic() < deadline:
        try:
            assert_logged_in(page)
            return
        except DoubaoLoginExpired as exc:
            last = exc
            if chat_url_is_logged_out(page.url or ""):
                raise
        except DoubaoCrawlError as exc:
            last = exc
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
            "behavior captcha detected; account needs human ticket/alert recovery "
            "(no auto-solve; sampling may API-fallback)"
        )
