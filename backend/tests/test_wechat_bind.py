"""WeChat MP bind QR / callback unit tests."""

from __future__ import annotations

import hashlib
import uuid
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from aperix_geo.api.routes import auth as auth_routes
from aperix_geo.services.wechat import bind_ticket as bind_mod
from aperix_geo.services.wechat.callback import (
    extract_bind_ticket_id,
    parse_callback_xml,
    verify_callback_signature,
)
from aperix_geo.services.wechat.config import wechat_configured
from aperix_geo.config import Settings


def _settings(**kwargs) -> Settings:
    base = {
        "wechat_app_id": "wx_app",
        "wechat_app_secret": "secret",
        "wechat_token": "tok123",
        "wechat_aes_key": "",
        "wechat_bind_ttl_seconds": 300,
    }
    base.update(kwargs)
    return Settings(**base)


def test_wechat_configured() -> None:
    assert not wechat_configured(_settings(wechat_app_id="", wechat_token="t"))
    assert wechat_configured(_settings())


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
@patch("aperix_geo.api.routes.auth.wechat_configured", return_value=False)
def test_create_bind_qr_requires_config(_cfg: MagicMock, _create: MagicMock) -> None:
    user = MagicMock(id=uuid.uuid4())
    with pytest.raises(HTTPException) as exc:
        auth_routes.create_wechat_bind_qr(user)
    assert exc.value.status_code == 503
    _create.assert_not_called()


@patch("aperix_geo.services.wechat.bind_ticket.fetch_user_info", return_value=None)
@patch("aperix_geo.services.wechat.bind_ticket.require_redis_client")
def test_complete_bind_from_scan_success(mock_redis: MagicMock, _info: MagicMock) -> None:
    user_id = uuid.uuid4()
    ticket_id = "ticket_ok_1"
    r = MagicMock()
    r.get.return_value = bind_mod._dump(
        bind_mod.BindTicket(
            ticket_id=ticket_id,
            user_id=str(user_id),
            status="pending",
            qrcode_url="https://example.com/qr",
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

    out = bind_mod.complete_bind_from_scan(db, ticket_id=ticket_id, open_id="oOPEN1")
    assert out is not None
    assert out.status == "bound"
    assert user.open_id == "oOPEN1"
    db.commit.assert_called_once()


@patch("aperix_geo.services.wechat.bind_ticket.require_redis_client")
def test_complete_bind_from_scan_conflict(mock_redis: MagicMock) -> None:
    owner = uuid.uuid4()
    other = uuid.uuid4()
    ticket_id = "ticket_conflict"
    r = MagicMock()
    r.get.return_value = bind_mod._dump(
        bind_mod.BindTicket(
            ticket_id=ticket_id,
            user_id=str(owner),
            status="pending",
            qrcode_url="https://example.com/qr",
            expires_in=300,
        )
    )
    r.ttl.return_value = 200
    mock_redis.return_value = r

    existing = MagicMock()
    existing.id = other
    db = MagicMock()
    db.execute.return_value.scalar_one_or_none.return_value = existing

    out = bind_mod.complete_bind_from_scan(db, ticket_id=ticket_id, open_id="oTAKEN")
    assert out is not None
    assert out.status == "failed"
    assert "其他账号" in out.error
    db.commit.assert_not_called()
