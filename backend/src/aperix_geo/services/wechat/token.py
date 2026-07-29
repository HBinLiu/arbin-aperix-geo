"""WeChat MP access_token (Redis-cached)."""

from __future__ import annotations

import logging

import httpx

from aperix_geo.config import Settings, get_settings
from aperix_geo.utils.cache.redis_kv import require_redis_client

logger = logging.getLogger(__name__)

_TOKEN_KEY = "aperix:wechat:access_token"
_TOKEN_SKEW_SECONDS = 120


class WechatError(RuntimeError):
    """WeChat Official Account API error."""


def get_access_token(settings: Settings | None = None) -> str:
    s = settings or get_settings()
    r = require_redis_client()
    cached = r.get(_TOKEN_KEY)
    if cached:
        return cached.decode() if isinstance(cached, bytes) else str(cached)

    url = "https://api.weixin.qq.com/cgi-bin/token"
    params = {
        "grant_type": "client_credential",
        "appid": s.wechat_app_id.strip(),
        "secret": s.wechat_app_secret.strip(),
    }
    with httpx.Client(timeout=s.wechat_http_timeout_s) as client:
        resp = client.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()

    token = str(data.get("access_token") or "").strip()
    if not token:
        err = data.get("errmsg") or data
        raise WechatError(f"Failed to get WeChat MP access_token: {err}")

    expires_in = int(data.get("expires_in") or 7200)
    ttl = max(60, expires_in - _TOKEN_SKEW_SECONDS)
    r.setex(_TOKEN_KEY, ttl, token)
    logger.info("WeChat MP access_token refreshed ttl=%s", ttl)
    return token
