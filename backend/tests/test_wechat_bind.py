"""WeChat MP OAuth bind / callback unit tests."""

from __future__ import annotations

import hashlib
import uuid
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from aperix_geo.api.routes import auth as auth_routes
from aperix_geo.config import Settings
from aperix_geo.services.wechat import bind_ticket as bind_mod
from aperix_geo.services.wechat.callback import (
    extract_bind_ticket_id,
    parse_callback_xml,
    verify_callback_signature,
)
from aperix_geo.services.wechat.config import wechat_configured, wechat_oauth_configured
from aperix_geo.services.wechat.oauth import OAuthUserInfo, build_oauth_authorize_url


def _settings(**kwargs) -> Settings:
    base = {
        "wechat_app_id": "wx_app",
        "wechat_app_secret": "secret",
        "wechat_token": "tok123",
        "wechat_aes_key": "",
        "wechat_oauth_redirect_uri": "https://api.example.com/api/v1/wechat/oauth/callback",
        "wechat_bind_ttl_seconds": 300,
    }
    base.update(kwargs)
    return Settings(**base)


def test_wechat_configured() -> None:
    assert not wechat_configured(_settings(wechat_app_id="", wechat_token="t"))
    assert wechat_configured(_settings())


def test_wechat_oauth_configured() -> None:
    assert not wechat_oauth_configured(_settings(wechat_oauth_redirect_uri=""))
    assert wechat_oauth_configured(_settings())


def test_build_oauth_authorize_url() -> None:
    url = build_oauth_authorize_url(state="ticket_abc", settings=_settings())
    assert "open.weixin.qq.com/connect/oauth2/authorize" in url
    assert "snsapi_userinfo" in url
    assert "state=ticket_abc" in url
    assert "wx_app" in url
    assert url.endswith("#wechat_redirect")


def test_verify_callback_signature() -> None:
    token, ts, nonce = "tok123", "1710000000", "nonce1"
    expected = hashlib.sha1("".join(sorted([token, ts, nonce])).encode()).hexdigest()
    assert verify_callback_signature(token=token, signature=expected, timestamp=ts, nonce=nonce)
    assert not verify_callback_signature(token=token, signature="bad", timestamp=ts, nonce=nonce)


def test_parse_callback_xml_and_ticket() -> None:
    xml = """
    <xml>
      <ToUserName><![CDATA[gh]]></ToUserName>
      <FromUserName><![CDATA[oABC]]></FromUserName>
      <MsgType><![CDATA[event]]></MsgType>
      <Event><![CDATA[SCAN]]></Event>
      <EventKey><![CDATA[ticket_xyz]]></EventKey>
    </xml>
    """
    fields = parse_callback_xml(xml)
    assert fields["FromUserName"] == "oABC"
    assert extract_bind_ticket_id(fields["Event"], fields["EventKey"]) == "ticket_xyz"
    assert extract_bind_ticket_id("subscribe", "qrscene_ticket_xyz") == "ticket_xyz"


@patch("aperix_geo.api.routes.auth.wechat_bind.create_bind_ticket")
@patch("aperix_geo.api.routes.auth.wechat_oauth_configured", return_value=False)
def test_create_bind_qr_requires_oauth_config(_cfg: MagicMock, _create: MagicMock) -> None:
    user = MagicMock(id=uuid.uuid4())
    with pytest.raises(HTTPException) as exc:
        auth_routes.create_wechat_bind_qr(user)
    assert exc.value.status_code == 503
    _create.assert_not_called()


@patch("aperix_geo.services.wechat.bind_ticket.require_redis_client")
def test_complete_bind_with_nickname(mock_redis: MagicMock) -> None:
    user_id = uuid.uuid4()
    ticket_id = "ticket_ok_1"
    r = MagicMock()
    r.get.return_value = bind_mod._dump(
        bind_mod.BindTicket(
            ticket_id=ticket_id,
            user_id=str(user_id),
            status="pending",
            authorize_url="https://open.weixin.qq.com/...",
            expires_in=300,
        )
    )
    r.ttl.return_value = 200
    mock_redis.return_value = r

    user = MagicMock()
    user.id = user_id
    user.is_active = True
    user.open_id = ""
    user.union_id = ""
    user.nick_name = ""

    db = MagicMock()
    db.execute.return_value.scalar_one_or_none.return_value = None
    db.get.return_value = user

    out = bind_mod.complete_bind(
        db,
        ticket_id=ticket_id,
        open_id="oOPEN1",
        nick_name="小明",
        union_id="uUNION",
    )
    assert out is not None
    assert out.status == "bound"
    assert user.open_id == "oOPEN1"
    assert user.nick_name == "小明"
    assert user.union_id == "uUNION"
    db.commit.assert_called_once()


@patch("aperix_geo.services.wechat.bind_ticket.require_redis_client")
def test_complete_bind_conflict(mock_redis: MagicMock) -> None:
    owner = uuid.uuid4()
    other = uuid.uuid4()
    ticket_id = "ticket_conflict"
    r = MagicMock()
    r.get.return_value = bind_mod._dump(
        bind_mod.BindTicket(
            ticket_id=ticket_id,
            user_id=str(owner),
            status="pending",
            authorize_url="https://open.weixin.qq.com/...",
            expires_in=300,
        )
    )
    r.ttl.return_value = 200
    mock_redis.return_value = r

    existing = MagicMock()
    existing.id = other
    db = MagicMock()
    db.execute.return_value.scalar_one_or_none.return_value = existing

    out = bind_mod.complete_bind(db, ticket_id=ticket_id, open_id="oTAKEN", nick_name="x")
    assert out is not None
    assert out.status == "failed"
    assert "其他账号" in out.error
    db.commit.assert_not_called()


@patch("aperix_geo.api.routes.wechat.complete_bind")
@patch("aperix_geo.api.routes.wechat.exchange_oauth_code")
@patch("aperix_geo.api.routes.wechat.wechat_oauth_configured", return_value=True)
def test_oauth_callback_success(
    _cfg: MagicMock,
    mock_exchange: MagicMock,
    mock_complete: MagicMock,
) -> None:
    from aperix_geo.api.routes.wechat import wechat_oauth_callback

    mock_exchange.return_value = OAuthUserInfo(open_id="o1", nick_name="阿宾", union_id="")
    mock_complete.return_value = bind_mod.BindTicket(
        ticket_id="t1",
        user_id=str(uuid.uuid4()),
        status="bound",
        authorize_url="https://x",
    )
    resp = wechat_oauth_callback(
        db=MagicMock(),
        code="CODE",
        state="t1",
        error="",
        error_description="",
    )
    assert resp.status_code == 200
    body = resp.body.decode()
    assert "绑定成功" in body
    assert "昵称：阿宾" in body
    assert "title-ok" in body
