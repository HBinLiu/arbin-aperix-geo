"""Send WeChat Official Account template messages."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

import httpx

from aperix_geo.config import Settings, get_settings
from aperix_geo.services.wechat.templates_config import TemplateDef, get_template, get_template_catalog
from aperix_geo.services.wechat.token import WechatError, get_access_token

logger = logging.getLogger(__name__)


def _truncate(value: str, max_chars: int) -> str:
    text = (value or "").strip().replace("\n", " ")
    if len(text) <= max_chars:
        return text
    if max_chars <= 1:
        return text[:max_chars]
    return text[: max_chars - 1] + "…"


def _auto_max_len(keyword: str) -> int:
    if keyword.startswith("thing"):
        return 20
    if keyword.startswith("phone_number"):
        return 17
    if keyword.startswith("amount"):
        return 32
    if keyword.startswith("character_string"):
        return 32
    if keyword.startswith("const"):
        return 20
    if keyword.startswith("time"):
        return 32
    return 64


def send_template_message(
    *,
    open_id: str,
    template_id: str,
    data: dict[str, Any],
    url: str = "",
    settings: Settings | None = None,
) -> None:
    """POST cgi-bin/message/template/send. Raises WechatError on API failure."""
    s = settings or get_settings()
    oid = open_id.strip()
    tid = template_id.strip()
    if not oid or not tid:
        raise WechatError("open_id and template_id are required")

    access_token = get_access_token(s)
    endpoint = f"https://api.weixin.qq.com/cgi-bin/message/template/send?access_token={access_token}"
    payload: dict[str, Any] = {
        "touser": oid,
        "template_id": tid,
        "data": data,
    }
    jump = (url or "").strip()
    if jump:
        payload["url"] = jump

    with httpx.Client(timeout=s.wechat_http_timeout_s) as client:
        resp = client.post(endpoint, json=payload)
        resp.raise_for_status()
        body = resp.json()

    errcode = int(body.get("errcode") or 0)
    if errcode != 0:
        raise WechatError(f"template/send failed errcode={errcode} errmsg={body.get('errmsg')}")
    logger.info("WeChat template sent openid=%s template=%s", oid[:8], tid[:12])


def build_template_data(
    template: TemplateDef,
    *,
    context: dict[str, str],
) -> dict[str, dict[str, str]]:
    """Fill template keywords from context sources or literals."""
    data: dict[str, dict[str, str]] = {}
    for field in template.fields:
        if field.value.strip():
            raw = field.value
        else:
            src = field.source.strip().lower()
            raw = context.get(src, "")
        limit = field.max_len if field.max_len > 0 else _auto_max_len(field.keyword)
        data[field.keyword] = {"value": _truncate(raw, limit)}
    return data


def resolve_quota_warn_template(
    *,
    settings: Settings | None = None,
) -> tuple[TemplateDef, str] | None:
    """Return (template, jump_url) for quota_warn, or None if missing."""
    s = settings or get_settings()
    template = get_template("quota_warn", settings=s)
    if template is None or not template.template_id.strip():
        return None

    catalog = get_template_catalog(settings=s)
    jump = ""
    base = catalog.jump_base_url.strip().rstrip("/")
    path = (template.url_path or "").strip()
    if base and path:
        jump = f"{base}{path if path.startswith('/') else '/' + path}"
    elif base and not path:
        jump = base
    return template, jump


def quota_warn_context(
    *,
    title: str,
    body: str,
    available: int,
    phone: str = "",
    reason: str = "",
) -> dict[str, str]:
    now = datetime.now(UTC).astimezone().strftime("%Y-%m-%d %H:%M")
    detail = body.strip() or f"当前可用 AI 请求 {available} 次"
    phone_val = (phone or "").strip() or "未绑定手机"
    # amount 类字段通常要数字/金额形态
    amount_val = str(max(available, 0))
    reason_val = (reason or title or detail).strip()
    return {
        "title": title,
        "body": detail,
        "time": now,
        "available": str(available),
        "phone": phone_val,
        "amount": amount_val,
        "reason": reason_val,
    }


def build_quota_warn_template_data(
    *,
    title: str,
    body: str,
    available: int,
    phone: str = "",
    reason: str = "",
    settings: Settings | None = None,
) -> tuple[TemplateDef, dict[str, dict[str, str]], str] | None:
    """Resolve quota_warn template + payload + jump URL. None if not configured."""
    resolved = resolve_quota_warn_template(settings=settings)
    if resolved is None:
        return None
    template, jump = resolved
    ctx = quota_warn_context(
        title=title,
        body=body,
        available=available,
        phone=phone,
        reason=reason,
    )
    data = build_template_data(template, context=ctx)
    return template, data, jump
