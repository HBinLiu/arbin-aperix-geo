"""Fetch WeChat MP user profile by openid."""

from __future__ import annotations

import logging
from dataclasses import dataclass

import httpx

from aperix_geo.config import Settings, get_settings
from aperix_geo.services.wechat.token import WechatError, get_access_token

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MpUserInfo:
    open_id: str
    nick_name: str = ""
    union_id: str = ""
    subscribe: bool = False


def fetch_user_info(open_id: str, *, settings: Settings | None = None) -> MpUserInfo | None:
    """Return user info when available; None if not subscribed / API soft-fail."""
    s = settings or get_settings()
    oid = open_id.strip()
    if not oid:
        return None

    access_token = get_access_token(s)
    url = "https://api.weixin.qq.com/cgi-bin/user/info"
    params = {"access_token": access_token, "openid": oid, "lang": "zh_CN"}
    with httpx.Client(timeout=s.wechat_http_timeout_s) as client:
        resp = client.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()

    errcode = data.get("errcode")
    if errcode not in (None, 0):
        logger.warning("WeChat MP user/info failed openid=%s err=%s", oid[:8], data.get("errmsg"))
        return None

    return MpUserInfo(
        open_id=str(data.get("openid") or oid).strip(),
        nick_name=str(data.get("nickname") or "").strip(),
        union_id=str(data.get("unionid") or "").strip(),
        subscribe=int(data.get("subscribe") or 0) == 1,
    )
