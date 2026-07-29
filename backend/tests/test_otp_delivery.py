"""OTP email / SMS delivery behavior."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from aperix_geo.config import Settings
from aperix_geo.services.auth.email import send_verification_email
from aperix_geo.services.auth.otp import email_use_dev_stub, send_code, sms_use_dev_stub
from aperix_geo.services.mail.smtp import smtp_configured


def _settings(**kwargs) -> Settings:
    base = {
        "env": "development",
        "otp_code_length": 6,
        "otp_code_ttl_seconds": 300,
        "otp_send_interval_seconds": 60,
        "sms_aliyun_access_key_id": "",
        "sms_aliyun_access_key_secret": "",
        "sms_aliyun_sign_name": "",
        "sms_aliyun_template_code": "",
        "smtp_host": "",
        "smtp_from": "",
        "smtp_user": "",
    }
    base.update(kwargs)
    return Settings(**base)


def test_smtp_configured() -> None:
    assert not smtp_configured(_settings())
    assert smtp_configured(_settings(smtp_host="smtp.example.com", smtp_from="a@b.com"))
    assert smtp_configured(_settings(smtp_host="smtp.example.com", smtp_user="u"))


def test_dev_stubs() -> None:
    assert email_use_dev_stub(_settings(env="development"))
    assert sms_use_dev_stub(_settings(env="local"))
    assert not email_use_dev_stub(_settings(env="production"))


@patch("aperix_geo.services.auth.otp.require_redis_client")
def test_send_code_email_dev_stub(mock_redis: MagicMock) -> None:
    r = MagicMock()
    r.exists.return_value = 0
    mock_redis.return_value = r
    ok, exposed = send_code(
        settings=_settings(env="development"),
        purpose="login",
        channel="email",
        target_raw="User@Example.com",
    )
    assert ok is True
    assert exposed is not None and len(exposed) == 6
    r.setex.assert_called()


@patch("aperix_geo.services.auth.email.send_smtp_email")
@patch("aperix_geo.services.auth.otp.require_redis_client")
def test_send_code_email_production_smtp(mock_redis: MagicMock, mock_send: MagicMock) -> None:
    r = MagicMock()
    r.exists.return_value = 0
    mock_redis.return_value = r
    settings = _settings(
        env="production",
        smtp_host="smtp.example.com",
        smtp_from="noreply@aperix.example",
        smtp_from_name="Aperix",
    )
    ok, exposed = send_code(
        settings=settings,
        purpose="login",
        channel="email",
        target_raw="user@example.com",
    )
    assert ok is True
    assert exposed is None
    mock_send.assert_called_once()
    kwargs = mock_send.call_args.kwargs
    assert kwargs["to_addrs"] == ["user@example.com"]
    assert "验证码" in kwargs["subject"]


@patch("aperix_geo.services.auth.otp.require_redis_client")
def test_send_code_email_production_without_smtp_fails(mock_redis: MagicMock) -> None:
    r = MagicMock()
    r.exists.return_value = 0
    mock_redis.return_value = r
    with pytest.raises(RuntimeError, match="SMTP"):
        send_code(
            settings=_settings(env="production"),
            purpose="login",
            channel="email",
            target_raw="user@example.com",
        )
    assert r.delete.call_count >= 1


@patch("aperix_geo.services.auth.otp.require_redis_client")
def test_send_code_phone_production_without_aliyun_fails(mock_redis: MagicMock) -> None:
    r = MagicMock()
    r.exists.return_value = 0
    mock_redis.return_value = r
    with pytest.raises(RuntimeError, match="短信未配置"):
        send_code(
            settings=_settings(env="production"),
            purpose="login",
            channel="phone",
            target_raw="13800138000",
        )


@patch("aperix_geo.services.auth.sms.send_verification_sms")
@patch("aperix_geo.services.auth.otp.require_redis_client")
def test_send_code_phone_production_when_configured(mock_redis: MagicMock, mock_sms: MagicMock) -> None:
    r = MagicMock()
    r.exists.return_value = 0
    mock_redis.return_value = r
    settings = _settings(
        env="production",
        sms_aliyun_access_key_id="id",
        sms_aliyun_access_key_secret="secret",
        sms_aliyun_sign_name="Aperix",
        sms_aliyun_template_code="SMS_123",
    )
    ok, exposed = send_code(
        settings=settings,
        purpose="login",
        channel="phone",
        target_raw="13800138000",
    )
    assert ok is True
    assert exposed is None
    mock_sms.assert_called_once()


def test_send_verification_email_builds_message() -> None:
    with patch("aperix_geo.services.auth.email.send_smtp_email") as mock_send:
        send_verification_email(
            _settings(smtp_host="h", smtp_from="f@x.com", otp_code_ttl_seconds=300),
            email="a@b.com",
            code="123456",
            purpose="login",
        )
        body = mock_send.call_args.kwargs["body"]
        assert "123456" in body
        assert "登录" in body
