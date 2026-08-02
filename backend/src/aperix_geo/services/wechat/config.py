"""WeChat MP configuration helpers."""

from __future__ import annotations

from aperix_geo.config import Settings, get_settings


def wechat_configured(settings: Settings | None = None) -> bool:
    """True when MP AppId/Secret/Token are set (message callback / templates)."""
    s = settings or get_settings()
    return bool(s.wechat_app_id.strip() and s.wechat_app_secret.strip() and s.wechat_token.strip())


def wechat_oauth_configured(settings: Settings | None = None) -> bool:
    """True when webpage OAuth bind can run (AppId/Secret + redirect URI)."""
    s = settings or get_settings()
    return bool(
        s.wechat_app_id.strip()
        and s.wechat_app_secret.strip()
        and s.wechat_oauth_redirect_uri.strip()
    )
