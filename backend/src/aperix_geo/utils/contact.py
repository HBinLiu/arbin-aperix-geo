"""Email and phone normalization."""

from __future__ import annotations


def normalize_email(value: str) -> str:
    s = value.strip().lower()
    if not s or "@" not in s:
        raise ValueError("invalid email")
    return s


def normalize_phone_cn(value: str) -> str:
    """大陆 11 位手机号，仅数字；可带 +86 前缀。"""
    digits = "".join(c for c in value if c.isdigit())
    if len(digits) == 13 and digits.startswith("86"):
        digits = digits[2:]
    if len(digits) != 11 or not digits.startswith("1"):
        raise ValueError("invalid phone")
    return digits


def mask_phone_cn(value: str) -> str:
    """大陆 11 位手机号中间 4 位脱敏，如 138****5678。"""
    raw = (value or "").strip()
    if not raw:
        return ""
    try:
        digits = normalize_phone_cn(raw)
    except ValueError:
        return raw
    return f"{digits[:3]}****{digits[7:]}"
