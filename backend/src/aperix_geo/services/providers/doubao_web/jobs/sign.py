"""Doubao a_bogus sign job: open chat, wait for frontierSign, sign query string."""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse

from aperix_geo.config import Settings
from aperix_geo.services.crawl_accounts.cookies import (
    job_payload_storage_state,
    job_requires_injected_session_cookies,
    storage_state_from_context,
    storage_state_has_session_cookies,
)
from aperix_geo.services.providers.doubao_web import selectors as sel
from aperix_geo.services.providers.doubao_web.errors import (
    DoubaoCrawlError,
    DoubaoLoginExpired,
    DoubaoNeedsHumanOps,
)
from aperix_geo.services.providers.doubao_web.runtime import (
    assert_no_captcha,
    job_error,
    job_ok,
    wait_until_logged_in,
)

logger = logging.getLogger(__name__)

_FINGERPRINT_KEYS = ("device_id", "fp", "web_id", "tea_uuid", "msToken")
_EMPTY = {"a_bogus": "", "ms_token": "", "fingerprint": {}, "query_string": ""}


def build_sign_payload(
    *,
    storage_state: dict[str, Any],
    settings: Settings,
    query_string: str = "",
    params: dict[str, str] | None = None,
) -> dict[str, Any]:
    timeout_s = min(90.0, float(settings.doubao_crawl_timeout_s))
    return {
        "mode": "sign",
        "storage_state": storage_state,
        "timeout_s": timeout_s,
        "chat_base_url": (settings.doubao_chat_base_url or sel.CHAT_URL).strip() or sel.CHAT_URL,
        "query_string": (query_string or "").strip(),
        "params": dict(params or {}),
        "device_id": (settings.doubao_web_device_id or "").strip(),
        "fp": (settings.doubao_web_fp or "").strip(),
        "web_id": (settings.doubao_web_web_id or "").strip(),
        "tea_uuid": (settings.doubao_web_tea_uuid or "").strip(),
    }


def _merge_fingerprint(
    *,
    payload: dict[str, Any],
    captured: dict[str, str],
    cookie_map: dict[str, str],
) -> dict[str, str]:
    out: dict[str, str] = {}
    for key in _FINGERPRINT_KEYS:
        for source in (
            str(payload.get(key) or "").strip(),
            captured.get(key, "").strip(),
            cookie_map.get(key, "").strip(),
        ):
            if source:
                out[key] = source
                break
    if "web_id" not in out and cookie_map.get("s_v_web_id"):
        out["web_id"] = cookie_map["s_v_web_id"]
    if "msToken" not in out and cookie_map.get("msToken"):
        out["msToken"] = cookie_map["msToken"]
    return out


def _cookie_map_from_list(cookies: list[Any]) -> dict[str, str]:
    out: dict[str, str] = {}
    for item in cookies:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        value = str(item.get("value") or "").strip()
        if name and value:
            out[name] = value
    return out


def _capture_fingerprint_from_url(url: str, sink: dict[str, str]) -> None:
    try:
        qs = parse_qs(urlparse(url).query)
    except Exception:
        return
    for key in _FINGERPRINT_KEYS:
        vals = qs.get(key) or []
        if vals and str(vals[0]).strip() and key not in sink:
            sink[key] = str(vals[0]).strip()


def run_doubao_sign_on_page(
    page: Any,
    context: Any,
    payload: dict[str, Any],
) -> dict[str, Any]:
    storage_state = job_payload_storage_state(payload)
    if storage_state is None:
        return job_error(DoubaoCrawlError("storage_state missing"), **_EMPTY)
    if job_requires_injected_session_cookies(payload) and not storage_state_has_session_cookies(
        storage_state
    ):
        return job_error(
            DoubaoLoginExpired("storage_state missing Doubao session cookies"),
            **_EMPTY,
        )

    base_url = str(payload.get("chat_base_url") or sel.CHAT_URL).strip() or sel.CHAT_URL
    timeout_s = float(payload.get("timeout_s") or 60)
    timeout_ms = min(90_000, int(timeout_s * 1000))
    captured: dict[str, str] = {}

    def _on_request(request: Any) -> None:
        try:
            url = str(getattr(request, "url", "") or "")
        except Exception:
            return
        if "doubao.com" in url:
            _capture_fingerprint_from_url(url, captured)

    try:
        page.on("request", _on_request)
        page.goto(base_url, wait_until="domcontentloaded", timeout=timeout_ms)
        wait_until_logged_in(page)
        assert_no_captcha(page)

        page.wait_for_function(
            "() => typeof window.byted_acrawler?.frontierSign === 'function'",
            timeout=min(30_000, timeout_ms),
        )
        page.wait_for_timeout(1_500)

        try:
            cookie_map = _cookie_map_from_list(context.cookies())
        except Exception:
            cookie_map = _cookie_map_from_list(list(storage_state.get("cookies") or []))

        fingerprint = _merge_fingerprint(
            payload=payload, captured=captured, cookie_map=cookie_map
        )

        query_string = str(payload.get("query_string") or "").strip()
        params = payload.get("params")
        if not query_string and isinstance(params, dict) and params:
            merged = {str(k): str(v) for k, v in params.items() if v is not None and str(v)}
            for key, value in fingerprint.items():
                merged.setdefault(key, value)
            query_string = urlencode(dict(sorted(merged.items())))

        a_bogus = ""
        if query_string:
            signature_obj = page.evaluate(
                """(qs) => {
                    try { return window.byted_acrawler.frontierSign(qs); }
                    catch (e) { return {error: String(e)}; }
                }""",
                query_string,
            )
            if isinstance(signature_obj, dict):
                if signature_obj.get("error"):
                    raise DoubaoCrawlError(f"frontierSign error: {signature_obj['error']}")
                a_bogus = str(
                    signature_obj.get("a_bogus") or signature_obj.get("X-Bogus") or ""
                ).strip()
            elif isinstance(signature_obj, str):
                a_bogus = signature_obj.strip()
            if not a_bogus:
                raise DoubaoCrawlError(f"frontierSign returned no a_bogus: {signature_obj!r}")

        return job_ok(
            a_bogus=a_bogus,
            ms_token=fingerprint.get("msToken", ""),
            fingerprint=fingerprint,
            query_string=query_string,
            storage_state=storage_state_from_context(
                context, fallback=storage_state, log_event="sign"
            ),
        )
    except DoubaoNeedsHumanOps as exc:
        return job_error(exc, **_EMPTY)
    except DoubaoCrawlError as exc:
        return job_error(exc, **_EMPTY)
    except Exception as exc:  # noqa: BLE001
        logger.exception("doubao sign job unexpected error")
        return job_error(exc, **_EMPTY)
    finally:
        try:
            page.remove_listener("request", _on_request)
        except Exception:
            pass
