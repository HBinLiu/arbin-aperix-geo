"""WeChat MP webpage OAuth (snsapi_userinfo) for account binding."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from urllib.parse import quote, urlencode

import httpx

from aperix_geo.config import Settings, get_settings
from aperix_geo.services.wechat.token import WechatError

logger = logging.getLogger(__name__)

_AUTHORIZE_BASE = "https://open.weixin.qq.com/connect/oauth2/authorize"
_TOKEN_URL = "https://api.weixin.qq.com/sns/oauth2/access_token"
_USERINFO_URL = "https://api.weixin.qq.com/sns/userinfo"


@dataclass(frozen=True)
class OAuthUserInfo:
    open_id: str
    nick_name: str = ""
    union_id: str = ""
    head_img_url: str = ""


def build_oauth_authorize_url(*, state: str, settings: Settings | None = None) -> str:
    """Build snsapi_userinfo authorize URL (open in WeChat; encode as QR on desktop)."""
    s = settings or get_settings()
    app_id = s.wechat_app_id.strip()
    redirect = s.wechat_oauth_redirect_uri.strip()
    sid = state.strip()
    if not app_id or not redirect or not sid:
        raise WechatError("WeChat OAuth is not configured (APP_ID / OAUTH_REDIRECT_URI)")

    query = urlencode(
        {
            "appid": app_id,
            "redirect_uri": redirect,
            "response_type": "code",
            "scope": "snsapi_userinfo",
            "state": sid,
        },
        quote_via=quote,
    )
    return f"{_AUTHORIZE_BASE}?{query}#wechat_redirect"


def exchange_oauth_code(code: str, *, settings: Settings | None = None) -> OAuthUserInfo:
    """Exchange authorization code for openid + nickname (snsapi_userinfo)."""
    s = settings or get_settings()
    c = code.strip()
    if not c:
        raise WechatError("Missing OAuth code")

    with httpx.Client(timeout=s.wechat_http_timeout_s) as client:
        token_resp = client.get(
            _TOKEN_URL,
            params={
                "appid": s.wechat_app_id.strip(),
                "secret": s.wechat_app_secret.strip(),
                "code": c,
                "grant_type": "authorization_code",
            },
        )
        token_resp.raise_for_status()
        token_data = token_resp.json()

    errcode = token_data.get("errcode")
    if errcode not in (None, 0):
        raise WechatError(f"OAuth token failed: {token_data.get('errmsg') or token_data}")

    access_token = str(token_data.get("access_token") or "").strip()
    open_id = str(token_data.get("openid") or "").strip()
    if not access_token or not open_id:
        raise WechatError("OAuth token response missing access_token/openid")

    with httpx.Client(timeout=s.wechat_http_timeout_s) as client:
        info_resp = client.get(
            _USERINFO_URL,
            params={
                "access_token": access_token,
                "openid": open_id,
                "lang": "zh_CN",
            },
        )
        info_resp.raise_for_status()
        info_data = info_resp.json()

    errcode = info_data.get("errcode")
    if errcode not in (None, 0):
        raise WechatError(f"OAuth userinfo failed: {info_data.get('errmsg') or info_data}")

    return OAuthUserInfo(
        open_id=str(info_data.get("openid") or open_id).strip(),
        nick_name=str(info_data.get("nickname") or "").strip(),
        union_id=str(info_data.get("unionid") or "").strip(),
        head_img_url=str(info_data.get("headimgurl") or "").strip(),
    )
