"""Create temporary bind QR codes via WeChat MP API."""

from __future__ import annotations

import logging
from urllib.parse import quote

import httpx

from aperix_geo.config import Settings, get_settings
from aperix_geo.services.wechat.token import WechatError, get_access_token

logger = logging.getLogger(__name__)


def create_bind_qrcode(
    *,
    scene_str: str,
    expire_seconds: int,
    settings: Settings | None = None,
) -> str:
    """Return the showqrcode URL for a temporary string-scene QR."""
    s = settings or get_settings()
    scene = scene_str.strip()
    if not scene or len(scene) > 64:
        raise WechatError("Invalid QR scene_str")

    access_token = get_access_token(s)
    url = f"https://api.weixin.qq.com/cgi-bin/qrcode/create?access_token={access_token}"
    payload = {
        "expire_seconds": int(expire_seconds),
        "action_name": "QR_STR_SCENE",
        "action_info": {"scene": {"scene_str": scene}},
    }
    with httpx.Client(timeout=s.wechat_http_timeout_s) as client:
        resp = client.post(url, json=payload)
        resp.raise_for_status()
        data = resp.json()

    ticket = str(data.get("ticket") or "").strip()
    if not ticket:
        err = data.get("errmsg") or data
        raise WechatError(f"Failed to create WeChat MP QR: {err}")

    show_url = f"https://mp.weixin.qq.com/cgi-bin/showqrcode?ticket={quote(ticket, safe='')}"
    logger.info("WeChat MP bind QR created scene=%s expire=%s", scene[:12], expire_seconds)
    return show_url
