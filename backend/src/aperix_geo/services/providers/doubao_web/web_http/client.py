"""Doubao Web completion client → job dict (via geo-web-crawl or httpx)."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlencode

import httpx

from aperix_geo.config import Settings, get_settings
from aperix_geo.services.providers.doubao_web.errors import DoubaoCrawlError, DoubaoLoginExpired
from aperix_geo.services.providers.doubao_web.runtime import (
    job_ok,
    raise_from_job,
    resolve_web_http_via,
    spawn_doubao_job,
)
from aperix_geo.services.providers.doubao_web.jobs.sign import build_sign_payload
from aperix_geo.services.providers.doubao_web.web_http.map_result import map_sse_events_to_fields
from aperix_geo.services.providers.doubao_web.web_http.protocol import (
    DEFAULT_BOT_ID,
    SAMANTHA_BASE_PARAMS,
    SAMANTHA_COMPLETION_URL,
    completion_body,
)
from aperix_geo.services.providers.doubao_web.jobs.http import build_web_http_payload


def request_a_bogus(
    *,
    storage_state: dict[str, Any],
    settings: Settings | None = None,
    query_string: str = "",
    params: dict[str, str] | None = None,
    extra: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Spawn geo-web-crawl mode=sign; return job dict with a_bogus / fingerprint."""
    settings = settings or get_settings()
    payload = build_sign_payload(
        storage_state=storage_state,
        settings=settings,
        query_string=query_string,
        params=params,
    )
    payload["platform"] = "doubao"
    if extra:
        payload.update(extra)
    job = spawn_doubao_job(payload, settings=settings, mode="sign")
    if job.get("ok"):
        return job
    raise_from_job(job)


def _cookie_header(storage_state: dict[str, Any]) -> str:
    parts: list[str] = []
    for item in storage_state.get("cookies") or []:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        value = str(item.get("value") or "")
        if name:
            parts.append(f"{name}={value}")
    return "; ".join(parts)


def complete_via_browser_job(
    *,
    prompt: str,
    storage_state: dict[str, Any],
    settings: Settings | None = None,
    extra: dict[str, str] | None = None,
) -> dict[str, Any]:
    settings = settings or get_settings()
    payload = build_web_http_payload(
        prompt=prompt, storage_state=storage_state, settings=settings
    )
    payload["platform"] = "doubao"
    if extra:
        payload.update(extra)
    job = spawn_doubao_job(
        payload,
        settings=settings,
        mode="http",
        timeout_s=float(settings.doubao_crawl_timeout_s),
    )
    if job.get("ok"):
        return job
    raise_from_job(job)


def complete_via_httpx(
    *,
    prompt: str,
    storage_state: dict[str, Any],
    settings: Settings | None = None,
    conversation_id: str = "0",
    extra: dict[str, str] | None = None,
) -> dict[str, Any]:
    settings = settings or get_settings()
    bot_id = (settings.doubao_web_bot_id or DEFAULT_BOT_ID).strip() or DEFAULT_BOT_ID
    params = dict(SAMANTHA_BASE_PARAMS)
    if settings.doubao_web_device_id:
        params["device_id"] = settings.doubao_web_device_id.strip()
    if settings.doubao_web_fp:
        params["fp"] = settings.doubao_web_fp.strip()
    if settings.doubao_web_web_id:
        params["web_id"] = settings.doubao_web_web_id.strip()
    if settings.doubao_web_tea_uuid:
        params["tea_uuid"] = settings.doubao_web_tea_uuid.strip()

    sign = request_a_bogus(
        storage_state=storage_state, settings=settings, params=params, extra=extra
    )
    for key, value in dict(sign.get("fingerprint") or {}).items():
        if value:
            params[key] = str(value)
    a_bogus = str(sign.get("a_bogus") or "").strip()
    if not a_bogus:
        raise DoubaoCrawlError("sign job returned empty a_bogus")

    url = f"{SAMANTHA_COMPLETION_URL}?{urlencode(dict(sorted(params.items())))}&a_bogus={a_bogus}"
    state = sign.get("storage_state") if isinstance(sign.get("storage_state"), dict) else storage_state
    headers = {
        "Accept": "*/*",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Content-Type": "application/json",
        "Cookie": _cookie_header(state),
        "Origin": "https://www.doubao.com",
        "Referer": "https://www.doubao.com/chat/",
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36"
        ),
        "agw-js-conv": "str, str",
    }
    body = completion_body(prompt, conversation_id=conversation_id, bot_id=bot_id)
    with httpx.Client(timeout=float(settings.doubao_crawl_timeout_s), follow_redirects=True) as client:
        response = client.post(url, headers=headers, json=body)

    if response.status_code in (401, 403):
        raise DoubaoLoginExpired(f"httpx completion HTTP {response.status_code}")
    if response.status_code != 200:
        raise DoubaoCrawlError(
            f"httpx completion HTTP {response.status_code}: {response.text[:400]}"
        )
    fields = map_sse_events_to_fields(response.text)
    if not str(fields.get("text") or "").strip():
        raise DoubaoCrawlError("httpx completion parsed empty text")
    return job_ok(
        text=fields["text"],
        search_queries=fields.get("search_queries") or [],
        source_urls=fields.get("source_urls") or [],
        conversation_id=fields.get("conversation_id") or "",
        storage_state=sign.get("storage_state"),
    )


def complete_web_http(
    *,
    prompt: str,
    storage_state: dict[str, Any],
    settings: Settings | None = None,
    extra: dict[str, str] | None = None,
) -> dict[str, Any]:
    settings = settings or get_settings()
    if resolve_web_http_via(settings) == "httpx":
        return complete_via_httpx(
            prompt=prompt, storage_state=storage_state, settings=settings, extra=extra
        )
    return complete_via_browser_job(
        prompt=prompt, storage_state=storage_state, settings=settings, extra=extra
    )
