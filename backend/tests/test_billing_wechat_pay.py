"""Tests for WeChat Pay helpers."""

from __future__ import annotations

import base64
import json
import uuid
from unittest.mock import MagicMock, patch

import httpx
import pytest
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.serialization import Encoding, NoEncryption, PrivateFormat
from cryptography.x509 import CertificateBuilder, Name, NameAttribute
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes as cert_hashes
import datetime

from aperix_geo.config import Settings
from aperix_geo.db.models import TenantPayOrder
from aperix_geo.services.billing.wechat_pay import (
    WechatPayError,
    create_native_prepay,
    handle_wechat_notification,
    is_wechat_pay_configured,
    order_out_trade_no,
    parse_out_trade_no,
)


def _generate_rsa_keypair() -> tuple[rsa.RSAPrivateKey, str]:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = private_key.private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption()).decode()
    public_key = private_key.public_key()
    subject = Name([NameAttribute(NameOID.COMMON_NAME, "wechat-platform")])
    cert = (
        CertificateBuilder()
        .subject_name(subject)
        .issuer_name(subject)
        .public_key(public_key)
        .serial_number(1)
        .not_valid_before(datetime.datetime.now(datetime.UTC) - datetime.timedelta(days=1))
        .not_valid_after(datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=365))
        .sign(private_key, cert_hashes.SHA256())
    )
    cert_pem = cert.public_bytes(Encoding.PEM).decode()
    return private_key, cert_pem


def _settings(private_pem: str, platform_pem: str) -> Settings:
    return Settings(
        wechat_pay_mch_id="1900000109",
        wechat_pay_app_id="wx1234567890abcdef",
        wechat_pay_api_v3_key="0123456789abcdef0123456789abcdef",
        wechat_pay_mch_cert_serial_no="merchant-serial",
        wechat_pay_private_key=private_pem,
        wechat_pay_platform_cert_pem=platform_pem,
        wechat_pay_platform_cert_serial="1",
        wechat_pay_notify_url="https://example.com/api/v1/billing/webhook/wechat",
    )


def test_order_out_trade_no_roundtrip() -> None:
    order_id = uuid.uuid4()
    assert parse_out_trade_no(order_out_trade_no(order_id)) == order_id


def test_is_wechat_pay_configured_requires_all_fields() -> None:
    private_key, platform_pem = _generate_rsa_keypair()
    private_pem = private_key.private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption()).decode()
    assert is_wechat_pay_configured(_settings(private_pem, platform_pem))
    assert not is_wechat_pay_configured(Settings())


@patch("aperix_geo.services.billing.wechat_pay.httpx.post")
def test_create_native_prepay_returns_code_url(mock_post: MagicMock) -> None:
    private_key, platform_pem = _generate_rsa_keypair()
    private_pem = private_key.private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption()).decode()
    settings = _settings(private_pem, platform_pem)
    order = TenantPayOrder(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        order_type="subscription",
        amount_cents=29900,
        status="pending",
    )
    mock_post.return_value = httpx.Response(
        200,
        json={"code_url": "weixin://wxpay/bizpayurl?pr=abc"},
        request=httpx.Request("POST", "https://api.mch.weixin.qq.com/v3/pay/transactions/native"),
    )

    code_url = create_native_prepay(order, settings=settings)
    assert code_url.startswith("weixin://")
    mock_post.assert_called_once()


def test_handle_wechat_notification_decrypts_success_payload() -> None:
    private_key, platform_pem = _generate_rsa_keypair()
    private_pem = private_key.private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption()).decode()
    settings = _settings(private_pem, platform_pem)
    order_id = uuid.uuid4()
    api_key = settings.wechat_pay_api_v3_key
    nonce = "nonce-123456789012"
    associated_data = "transaction"
    payload = {
        "trade_state": "SUCCESS",
        "out_trade_no": order_out_trade_no(order_id),
        "transaction_id": "4200001234567890",
        "amount": {"total": 29900, "currency": "CNY"},
    }
    ciphertext = base64.b64encode(
        AESGCM(api_key.encode("utf-8")).encrypt(
            nonce.encode("utf-8"),
            json.dumps(payload, separators=(",", ":")).encode("utf-8"),
            associated_data.encode("utf-8"),
        )
    ).decode("ascii")
    body = json.dumps(
        {
            "id": "notify-id",
            "create_time": "2026-01-01T00:00:00+08:00",
            "resource_type": "encrypt-resource",
            "event_type": "TRANSACTION.SUCCESS",
            "resource": {
                "algorithm": "AEAD_AES_256_GCM",
                "ciphertext": ciphertext,
                "associated_data": associated_data,
                "nonce": nonce,
            },
        },
        separators=(",", ":"),
    ).encode("utf-8")
    timestamp = "1700000000"
    wx_nonce = "wx-nonce"
    signature = base64.b64encode(
        private_key.sign(
            f"{timestamp}\n{wx_nonce}\n{body.decode('utf-8')}\n".encode("utf-8"),
            padding.PKCS1v15(),
            hashes.SHA256(),
        )
    ).decode("ascii")

    result = handle_wechat_notification(
        body,
        signature=signature,
        timestamp=timestamp,
        nonce=wx_nonce,
        serial="1",
        settings=settings,
    )
    assert result.order_id == order_id
    assert result.transaction_id == "4200001234567890"
    assert result.amount_cents == 29900


def test_handle_wechat_notification_rejects_bad_signature() -> None:
    private_key, platform_pem = _generate_rsa_keypair()
    private_pem = private_key.private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption()).decode()
    settings = _settings(private_pem, platform_pem)
    body = b'{"event_type":"TRANSACTION.SUCCESS"}'
    with pytest.raises(WechatPayError, match="signature"):
        handle_wechat_notification(
            body,
            signature="invalid",
            timestamp="1",
            nonce="n",
            serial="1",
            settings=settings,
        )
