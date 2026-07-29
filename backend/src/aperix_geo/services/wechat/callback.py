"""WeChat MP callback signature + XML parse (+ optional AES decrypt)."""

from __future__ import annotations

import base64
import hashlib
import logging
import struct
import xml.etree.ElementTree as ET
from typing import Any

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from aperix_geo.config import Settings, get_settings

logger = logging.getLogger(__name__)


def verify_callback_signature(
    *,
    token: str,
    signature: str,
    timestamp: str,
    nonce: str,
    encrypt: str | None = None,
) -> bool:
    """Verify WeChat GET/POST callback signature (plaintext or msg_signature with encrypt)."""
    parts = [token.strip(), timestamp.strip(), nonce.strip()]
    if encrypt is not None:
        parts.append(encrypt)
    digest = hashlib.sha1("".join(sorted(parts)).encode("utf-8")).hexdigest()
    return digest == (signature or "").strip()


def parse_callback_xml(raw: str | bytes) -> dict[str, str]:
    """Parse WeChat XML body into a flat string map of child tags."""
    text = raw.decode("utf-8") if isinstance(raw, bytes) else raw
    root = ET.fromstring(text)
    out: dict[str, str] = {}
    for child in root:
        out[child.tag] = (child.text or "").strip()
    return out


def maybe_decrypt_message(fields: dict[str, str], *, settings: Settings | None = None) -> dict[str, str]:
    """If Encrypt present and AES key configured, decrypt and re-parse inner XML."""
    s = settings or get_settings()
    encrypt = fields.get("Encrypt", "").strip()
    aes_key = s.wechat_aes_key.strip()
    if not encrypt:
        return fields
    if not aes_key:
        raise ValueError("Encrypted WeChat callback received but WECHAT_AES_KEY is empty")
    plain_xml = decrypt_wechat_message(
        encrypt,
        aes_key=aes_key,
        app_id=s.wechat_app_id.strip(),
    )
    return parse_callback_xml(plain_xml)


def decrypt_wechat_message(encrypt_b64: str, *, aes_key: str, app_id: str) -> str:
    """Decrypt WeChat safe-mode Encrypt payload → XML string."""
    key = base64.b64decode(aes_key + "=")
    if len(key) != 32:
        raise ValueError("Invalid WECHAT_AES_KEY length")
    iv = key[:16]
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
    decryptor = cipher.decryptor()
    decrypted = decryptor.update(base64.b64decode(encrypt_b64)) + decryptor.finalize()
    pad = decrypted[-1]
    if isinstance(pad, str):  # pragma: no cover
        pad = ord(pad)
    content = decrypted[:-pad]
    xml_len = struct.unpack("!I", content[16:20])[0]
    xml = content[20 : 20 + xml_len].decode("utf-8")
    from_app_id = content[20 + xml_len :].decode("utf-8")
    if app_id and from_app_id != app_id:
        raise ValueError("WeChat decrypt app_id mismatch")
    return xml


def extract_bind_ticket_id(event: str, event_key: str) -> str | None:
    """Extract bind ticket from subscribe/SCAN EventKey."""
    key = (event_key or "").strip()
    if not key:
        return None
    ev = (event or "").strip().lower()
    if ev == "subscribe" and key.startswith("qrscene_"):
        return key.removeprefix("qrscene_").strip() or None
    if ev == "scan":
        return key or None
    return None


def event_fields(msg: dict[str, str]) -> dict[str, Any]:
    return {
        "msg_type": msg.get("MsgType", ""),
        "event": msg.get("Event", ""),
        "event_key": msg.get("EventKey", ""),
        "open_id": msg.get("FromUserName", ""),
        "ticket_id": extract_bind_ticket_id(msg.get("Event", ""), msg.get("EventKey", "")),
    }
