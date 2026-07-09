"""WeChat Pay V3 — Native (QR code) prepay and async notification."""

from __future__ import annotations

import base64
import json
import logging
import secrets
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey
from cryptography.hazmat.primitives.asymmetric.types import CertificatePublicKeyTypes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.x509 import load_pem_x509_certificate

from aperix_geo.config import Settings, get_settings
from aperix_geo.db.models import TenantPayOrder

logger = logging.getLogger(__name__)

_WECHAT_API_BASE = "https://api.mch.weixin.qq.com"
_NATIVE_PATH = "/v3/pay/transactions/native"

_ORDER_DESCRIPTIONS: dict[str, str] = {
    "subscription": "Aperix 订阅",
    "subscription_renewal": "Aperix 订阅续费",
    "plan_change": "Aperix 套餐变更",
    "usage_pack": "Aperix AI 配额包",
}


class WechatPayError(Exception):
    """WeChat Pay API or notification handling error."""


@dataclass(frozen=True)
class WechatNotifyResult:
    order_id: uuid.UUID
    transaction_id: str
    amount_cents: int


def is_wechat_pay_configured(settings: Settings | None = None) -> bool:
    settings = settings or get_settings()
    return bool(
        settings.wechat_pay_mch_id.strip()
        and settings.wechat_pay_app_id.strip()
        and settings.wechat_pay_api_v3_key.strip()
        and settings.wechat_pay_mch_cert_serial_no.strip()
        and settings.wechat_pay_notify_url.strip()
        and _load_private_key(settings) is not None
        and _load_platform_public_key(settings) is not None
    )


def order_out_trade_no(order_id: uuid.UUID) -> str:
    return order_id.hex


def parse_out_trade_no(value: str) -> uuid.UUID:
    cleaned = value.strip()
    if len(cleaned) != 32:
        raise WechatPayError(f"Invalid out_trade_no: {value!r}")
    return uuid.UUID(hex=cleaned)


def create_native_prepay(order: TenantPayOrder, *, settings: Settings | None = None) -> str:
    """Create a WeChat Native prepay order and return code_url for QR display."""
    settings = settings or get_settings()
    if not is_wechat_pay_configured(settings):
        raise WechatPayError("WeChat Pay is not configured")

    private_key = _load_private_key(settings)
    if private_key is None:
        raise WechatPayError("WeChat Pay merchant private key is missing")

    description = _ORDER_DESCRIPTIONS.get(order.order_type, "Aperix 订单")
    payload = {
        "appid": settings.wechat_pay_app_id.strip(),
        "mchid": settings.wechat_pay_mch_id.strip(),
        "description": description,
        "out_trade_no": order_out_trade_no(order.id),
        "notify_url": settings.wechat_pay_notify_url.strip(),
        "amount": {"total": order.amount_cents, "currency": "CNY"},
    }
    body = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
    auth = _build_authorization(
        settings.wechat_pay_mch_id.strip(),
        settings.wechat_pay_mch_cert_serial_no.strip(),
        private_key,
        method="POST",
        url_path=_NATIVE_PATH,
        body=body,
    )
    response = httpx.post(
        f"{_WECHAT_API_BASE}{_NATIVE_PATH}",
        content=body.encode("utf-8"),
        headers={
            "Authorization": auth,
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
        timeout=settings.wechat_pay_timeout_s,
    )
    if response.status_code >= 400:
        logger.warning("WeChat Native prepay failed status=%s body=%s", response.status_code, response.text)
        raise WechatPayError(_format_api_error(response))

    data = response.json()
    code_url = str(data.get("code_url", "")).strip()
    if not code_url:
        raise WechatPayError("WeChat Pay did not return code_url")
    return code_url


def handle_wechat_notification(
    body: bytes,
    *,
    signature: str,
    timestamp: str,
    nonce: str,
    serial: str,
    settings: Settings | None = None,
) -> WechatNotifyResult:
    """Verify and decrypt a WeChat Pay async notification."""
    settings = settings or get_settings()
    if not is_wechat_pay_configured(settings):
        raise WechatPayError("WeChat Pay is not configured")

    platform_key = _load_platform_public_key(settings)
    if platform_key is None:
        raise WechatPayError("WeChat Pay platform certificate is missing")

    _verify_signature(platform_key, timestamp=timestamp, nonce=nonce, body=body, signature_b64=signature)
    if serial.strip() and serial.strip() != settings.wechat_pay_platform_cert_serial.strip():
        configured_serial = settings.wechat_pay_platform_cert_serial.strip()
        if configured_serial:
            logger.warning("WeChat notify serial mismatch got=%s expected=%s", serial, configured_serial)

    envelope = json.loads(body.decode("utf-8"))
    if envelope.get("event_type") != "TRANSACTION.SUCCESS":
        raise WechatPayError(f"Unsupported event_type: {envelope.get('event_type')!r}")

    resource = envelope.get("resource") or {}
    plaintext = _decrypt_resource(
        settings.wechat_pay_api_v3_key.strip(),
        nonce=str(resource.get("nonce", "")),
        ciphertext=str(resource.get("ciphertext", "")),
        associated_data=str(resource.get("associated_data", "")),
    )
    trade_state = str(plaintext.get("trade_state", "")).strip()
    if trade_state != "SUCCESS":
        raise WechatPayError(f"Unexpected trade_state: {trade_state!r}")

    order_id = parse_out_trade_no(str(plaintext.get("out_trade_no", "")))
    transaction_id = str(plaintext.get("transaction_id", "")).strip()
    if not transaction_id:
        raise WechatPayError("Missing transaction_id in notification")

    amount = plaintext.get("amount") or {}
    total = int(amount.get("total", 0))
    if total <= 0:
        raise WechatPayError("Invalid amount in notification")

    return WechatNotifyResult(order_id=order_id, transaction_id=transaction_id, amount_cents=total)


def _format_api_error(response: httpx.Response) -> str:
    try:
        data = response.json()
        message = data.get("message") or data.get("detail") or response.text
        return str(message)
    except Exception:
        return response.text or f"WeChat Pay HTTP {response.status_code}"


def _load_private_key(settings: Settings) -> RSAPrivateKey | None:
    pem = settings.wechat_pay_private_key.strip()
    if not pem and settings.wechat_pay_private_key_path.strip():
        path = Path(settings.wechat_pay_private_key_path.strip())
        if path.is_file():
            pem = path.read_text(encoding="utf-8")
    if not pem:
        return None
    key = serialization.load_pem_private_key(pem.encode("utf-8"), password=None)
    if not isinstance(key, RSAPrivateKey):
        raise WechatPayError("WeChat Pay private key must be RSA")
    return key


def _load_platform_public_key(settings: Settings) -> CertificatePublicKeyTypes | None:
    pem = settings.wechat_pay_platform_cert_pem.strip()
    if not pem and settings.wechat_pay_platform_cert_path.strip():
        path = Path(settings.wechat_pay_platform_cert_path.strip())
        if path.is_file():
            pem = path.read_text(encoding="utf-8")
    if not pem:
        return None
    cert = load_pem_x509_certificate(pem.encode("utf-8"))
    return cert.public_key()


def _build_authorization(
    mch_id: str,
    serial_no: str,
    private_key: RSAPrivateKey,
    *,
    method: str,
    url_path: str,
    body: str,
) -> str:
    timestamp = str(int(time.time()))
    nonce = secrets.token_hex(16)
    message = f"{method}\n{url_path}\n{timestamp}\n{nonce}\n{body}\n"
    signature = base64.b64encode(
        private_key.sign(message.encode("utf-8"), padding.PKCS1v15(), hashes.SHA256())
    ).decode("ascii")
    return (
        f'WECHATPAY2-SHA256-RSA2048 mchid="{mch_id}",nonce_str="{nonce}",'
        f'signature="{signature}",timestamp="{timestamp}",serial_no="{serial_no}"'
    )


def _verify_signature(
    public_key: CertificatePublicKeyTypes,
    *,
    timestamp: str,
    nonce: str,
    body: bytes,
    signature_b64: str,
) -> None:
    message = f"{timestamp}\n{nonce}\n{body.decode('utf-8')}\n"
    try:
        public_key.verify(
            base64.b64decode(signature_b64),
            message.encode("utf-8"),
            padding.PKCS1v15(),
            hashes.SHA256(),
        )
    except Exception as exc:
        raise WechatPayError("Invalid WeChat Pay notification signature") from exc


def _decrypt_resource(api_v3_key: str, *, nonce: str, ciphertext: str, associated_data: str) -> dict[str, Any]:
    if len(api_v3_key) != 32:
        raise WechatPayError("WECHAT_PAY_API_V3_KEY must be 32 bytes")
    if not nonce or not ciphertext:
        raise WechatPayError("Missing encrypted resource in notification")
    aesgcm = AESGCM(api_v3_key.encode("utf-8"))
    try:
        plaintext = aesgcm.decrypt(
            nonce.encode("utf-8"),
            base64.b64decode(ciphertext),
            associated_data.encode("utf-8"),
        )
    except Exception as exc:
        raise WechatPayError("Failed to decrypt WeChat Pay notification") from exc
    return json.loads(plaintext.decode("utf-8"))
