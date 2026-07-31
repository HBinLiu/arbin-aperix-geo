"""Email / phone OTP login (verify = auto register)."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from aperix_geo.api.routes import auth as auth_routes
from aperix_geo.db.models import User
from aperix_geo.schemas.auth import LoginWithOtpRequest, SendCodeRequest


def _request(*, host: str = "127.0.0.1") -> MagicMock:
    req = MagicMock()
    req.headers = {}
    req.client = MagicMock(host=host)
    return req


def _user(*, email: str = "", phone: str = "") -> User:
    return User(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        email=email,
        phone=phone,
    )


@patch("aperix_geo.api.routes.auth.get_settings")
@patch.object(auth_routes.otp_svc, "send_code", return_value=(True, "123456"))
def test_send_code_login_email_sends(mock_send: MagicMock, mock_settings: MagicMock) -> None:
    mock_settings.return_value = MagicMock(env="development")
    body = SendCodeRequest(purpose="login", channel="email", target="User@Example.com")
    resp = auth_routes.send_code(body, _request())
    assert resp.ok is True
    assert resp.dev_code == "123456"
    mock_send.assert_called_once()
    assert mock_send.call_args.kwargs["purpose"] == "login"
    assert mock_send.call_args.kwargs["channel"] == "email"
    assert mock_send.call_args.kwargs["client_ip"] == "127.0.0.1"


@patch("aperix_geo.api.routes.auth.get_settings")
@patch.object(auth_routes.otp_svc, "send_code", return_value=(True, "654321"))
def test_send_code_login_phone_sends(mock_send: MagicMock, mock_settings: MagicMock) -> None:
    mock_settings.return_value = MagicMock(env="development")
    body = SendCodeRequest(purpose="login", channel="phone", target="13800138000")
    resp = auth_routes.send_code(body, _request(host="203.0.113.1"))
    assert resp.ok is True
    assert resp.dev_code == "654321"
    mock_send.assert_called_once()
    assert mock_send.call_args.kwargs["client_ip"] == "203.0.113.1"


@patch("aperix_geo.api.routes.auth.create_access_token", return_value="tok")
@patch("aperix_geo.api.routes.auth.get_settings")
def test_login_with_otp_email_existing_user(mock_settings: MagicMock, mock_token: MagicMock) -> None:
    mock_settings.return_value = MagicMock()
    existing = _user(email="user@example.com")
    db = MagicMock()
    body = LoginWithOtpRequest(channel="email", target="user@example.com", code="123456")
    with patch.object(auth_routes.otp_svc, "verify_code", return_value=True):
        with patch.object(auth_routes, "_users_by_email", return_value=[existing]):
            resp = auth_routes.login_with_otp(body, db)
    assert resp.access_token == "tok"
    mock_token.assert_called_once_with(user_id=existing.id, tenant_id=existing.tenant_id)
    db.add.assert_not_called()


@patch("aperix_geo.api.routes.auth.create_access_token", return_value="tok-new")
@patch("aperix_geo.api.routes.auth.get_settings")
def test_login_with_otp_email_auto_register(mock_settings: MagicMock, mock_token: MagicMock) -> None:
    mock_settings.return_value = MagicMock()
    db = MagicMock()
    body = LoginWithOtpRequest(channel="email", target="new@example.com", code="123456")
    with patch.object(auth_routes.otp_svc, "verify_code", return_value=True):
        with patch.object(auth_routes, "_users_by_email", return_value=[]):
            resp = auth_routes.login_with_otp(body, db)
    assert resp.access_token == "tok-new"
    assert db.add.call_count == 2
    db.commit.assert_called_once()
    new_user = db.add.call_args_list[1].args[0]
    assert isinstance(new_user, User)
    assert new_user.email == "new@example.com"
    assert new_user.phone == ""


@patch("aperix_geo.api.routes.auth.create_access_token", return_value="tok-phone")
@patch("aperix_geo.api.routes.auth.get_settings")
def test_login_with_otp_phone_auto_register(mock_settings: MagicMock, _mock_token: MagicMock) -> None:
    mock_settings.return_value = MagicMock()
    db = MagicMock()
    body = LoginWithOtpRequest(channel="phone", target="13800138000", code="123456")
    with patch.object(auth_routes.otp_svc, "verify_code", return_value=True):
        with patch.object(auth_routes, "_user_by_phone", return_value=None):
            resp = auth_routes.login_with_otp(body, db)
    assert resp.access_token == "tok-phone"
    new_user = db.add.call_args_list[1].args[0]
    assert new_user.phone == "13800138000"
    assert new_user.email == ""


@patch("aperix_geo.api.routes.auth.get_settings")
def test_login_with_otp_rejects_bad_code(mock_settings: MagicMock) -> None:
    mock_settings.return_value = MagicMock()
    db = MagicMock()
    body = LoginWithOtpRequest(channel="email", target="user@example.com", code="000000")
    with patch.object(auth_routes.otp_svc, "verify_code", return_value=False):
        with pytest.raises(HTTPException) as exc:
            auth_routes.login_with_otp(body, db)
    assert exc.value.status_code == 400
