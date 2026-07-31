"""OTP multi-dimensional rate limits."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from aperix_geo.config import Settings
from aperix_geo.services.auth.otp import send_code
from aperix_geo.utils.client_ip import client_ip_from_request


def _settings(**kwargs) -> Settings:
    base = {
        "env": "development",
        "otp_code_length": 6,
        "otp_code_ttl_seconds": 300,
        "otp_send_interval_seconds": 60,
        "otp_phone_daily_limit": 8,
        "otp_email_daily_limit": 20,
        "otp_ip_hourly_limit": 20,
        "otp_ip_daily_limit": 50,
        "otp_sms_global_daily_limit": 1000,
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


def _redis_ok() -> MagicMock:
    r = MagicMock()
    r.exists.return_value = 0
    r.get.return_value = None
    r.incr.side_effect = lambda _key: 1
    return r


def test_client_ip_from_forwarded_for() -> None:
    req = MagicMock()
    req.headers = {"x-forwarded-for": "203.0.113.9, 10.0.0.1"}
    req.client = MagicMock(host="127.0.0.1")
    assert client_ip_from_request(req) == "203.0.113.9"


def test_client_ip_falls_back_to_peer() -> None:
    req = MagicMock()
    req.headers = {}
    req.client = MagicMock(host="198.51.100.2")
    assert client_ip_from_request(req) == "198.51.100.2"


@patch("aperix_geo.services.auth.otp.require_redis_client")
def test_send_code_records_counters_on_success(mock_redis: MagicMock) -> None:
    r = _redis_ok()
    mock_redis.return_value = r
    ok, exposed = send_code(
        settings=_settings(),
        purpose="login",
        channel="phone",
        target_raw="13800138000",
        client_ip="203.0.113.10",
    )
    assert ok is True
    assert exposed is not None
    assert r.incr.call_count >= 3  # target day + ip hour + ip day + sms global
    assert r.expire.call_count >= 1


@patch("aperix_geo.services.auth.otp.require_redis_client")
def test_send_code_phone_daily_limit(mock_redis: MagicMock) -> None:
    r = _redis_ok()

    def get_side_effect(key: str):
        if ":otp_day:v1:phone:" in key:
            return "8"
        return None

    r.get.side_effect = get_side_effect
    mock_redis.return_value = r
    with pytest.raises(ValueError, match="发送过于频繁"):
        send_code(
            settings=_settings(otp_phone_daily_limit=8),
            purpose="login",
            channel="phone",
            target_raw="13800138000",
            client_ip="203.0.113.11",
        )
    r.incr.assert_not_called()


@patch("aperix_geo.services.auth.otp.require_redis_client")
def test_send_code_ip_hourly_limit(mock_redis: MagicMock) -> None:
    r = _redis_ok()

    def get_side_effect(key: str):
        if ":otp_ip_h:v1:" in key:
            return "20"
        return None

    r.get.side_effect = get_side_effect
    mock_redis.return_value = r
    with pytest.raises(ValueError, match="发送过于频繁"):
        send_code(
            settings=_settings(otp_ip_hourly_limit=20),
            purpose="login",
            channel="email",
            target_raw="a@b.com",
            client_ip="203.0.113.12",
        )


@patch("aperix_geo.services.auth.otp.require_redis_client")
def test_send_code_sms_global_daily_limit(mock_redis: MagicMock) -> None:
    r = _redis_ok()

    def get_side_effect(key: str):
        if ":otp_sms_global:v1:" in key:
            return "1000"
        return None

    r.get.side_effect = get_side_effect
    mock_redis.return_value = r
    with pytest.raises(ValueError, match="发送过于频繁"):
        send_code(
            settings=_settings(otp_sms_global_daily_limit=1000),
            purpose="login",
            channel="phone",
            target_raw="13800138001",
            client_ip="203.0.113.13",
        )


@patch("aperix_geo.services.auth.otp.require_redis_client")
def test_send_code_sms_global_limit_skips_email(mock_redis: MagicMock) -> None:
    r = _redis_ok()

    def get_side_effect(key: str):
        if ":otp_sms_global:v1:" in key:
            return "9999"
        return None

    r.get.side_effect = get_side_effect
    mock_redis.return_value = r
    ok, _ = send_code(
        settings=_settings(otp_sms_global_daily_limit=1),
        purpose="login",
        channel="email",
        target_raw="ok@example.com",
        client_ip="203.0.113.14",
    )
    assert ok is True


@patch("aperix_geo.services.auth.otp.require_redis_client")
def test_send_code_limit_zero_disables_dimension(mock_redis: MagicMock) -> None:
    r = _redis_ok()
    r.get.return_value = "9999"
    mock_redis.return_value = r
    ok, _ = send_code(
        settings=_settings(
            otp_phone_daily_limit=0,
            otp_ip_hourly_limit=0,
            otp_ip_daily_limit=0,
            otp_sms_global_daily_limit=0,
        ),
        purpose="login",
        channel="phone",
        target_raw="13800138002",
        client_ip="203.0.113.15",
    )
    assert ok is True
    r.incr.assert_not_called()
