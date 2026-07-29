"""WeChat MP configuration helpers."""

from __future__ import annotations

from aperix_geo.config import Settings, get_settings


def wechat_configured(settings: Settings | None = None) -> bool:
    s = settings or get_settings()
    return bool(s.wechat_app_id.strip() and s.wechat_app_secret.strip() and s.wechat_token.strip())
