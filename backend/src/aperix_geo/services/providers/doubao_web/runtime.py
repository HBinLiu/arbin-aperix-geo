"""Doubao crawl runtime: modes, transport, job envelopes, page guards."""

from __future__ import annotations

from typing import Any, Literal

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
    **empty_fields: Any,
) -> dict[str, Any]:
    if human_ops is None:
        human_ops = isinstance(exc, DoubaoNeedsHumanOps)
    out: dict[str, Any] = {
        "ok": False,
        "error_type": type(exc).__name__,
        "error": str(exc),
        "human_ops": bool(human_ops),
        "storage_state": None,
    }
    out.update(empty_fields)
    return out


def raise_from_job(job: dict[str, Any]) -> None:
    err_type = str(job.get("error_type") or "DoubaoCrawlError")
    err_msg = str(job.get("error") or "job failed")
    if err_type == "DoubaoCaptchaRequired":
        raise DoubaoCaptchaRequired(err_msg)
    if err_type == "DoubaoLoginExpired":
        raise DoubaoLoginExpired(err_msg)
    if err_type == "DoubaoShareError":
        raise DoubaoShareError(err_msg)
    if job.get("human_ops") or err_type in _HUMAN_OPS_TYPES:
        raise DoubaoNeedsHumanOps(err_msg)
    raise DoubaoCrawlError(err_msg)


def is_human_ops_job(job: dict[str, Any]) -> bool:
    if job.get("human_ops"):
        return True
    return str(job.get("error_type") or "") in _HUMAN_OPS_TYPES


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


def assert_logged_in(page: Any) -> None:
    url = (page.url or "").lower()
    if "login" in url or "passport" in url:
        raise DoubaoLoginExpired(f"redirected to login: {page.url}")
    login_btn = page.get_by_role("button", name=sel.LOGIN_HINT)
    composer = _composer(page)
    if login_btn.count() > 0 and composer is None:
        raise DoubaoLoginExpired("login UI visible; storage_state expired")


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
