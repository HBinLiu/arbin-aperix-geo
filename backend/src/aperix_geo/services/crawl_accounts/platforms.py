"""Platform ids and start-URL helpers for geo crawl accounts."""

from __future__ import annotations

import re

from aperix_geo.config import Settings, get_settings

PLATFORM_DOUBAO = "doubao"
PLATFORM_DEEPSEEK = "deepseek"
PLATFORM_QIANWEN = "qianwen"

KNOWN_PLATFORMS = frozenset({PLATFORM_DOUBAO, PLATFORM_DEEPSEEK, PLATFORM_QIANWEN})

LOGIN_REASONS = frozenset({"login_expired", "captcha"})
DEFAULT_LOGIN_REASON = "login_expired"

_REASON_IN_TEXT = re.compile(
    r"(?:^auto:|/reason=|\breason=)(captcha|login_expired)\b",
    re.IGNORECASE,
)


def normalize_platform(raw: str | None) -> str:
    p = (raw or "").strip().lower() or PLATFORM_DOUBAO
    return p


def normalize_login_reason(raw: str | None) -> str:
    value = (raw or DEFAULT_LOGIN_REASON).strip().lower()
    return value if value in LOGIN_REASONS else DEFAULT_LOGIN_REASON


def login_reason_from_ticket_text(error_text: str | None) -> str:
    """Recover captcha vs login_expired from ticket error_text (no dedicated column)."""
    text = (error_text or "").strip()
    if not text:
        return DEFAULT_LOGIN_REASON
    if text.startswith("auto:captcha") or "auto:captcha:" in text[:40]:
        return "captcha"
    match = _REASON_IN_TEXT.search(text)
    if match:
        return normalize_login_reason(match.group(1))
    if "captcha" in text.lower() and "login_expired" not in text.lower()[:80]:
        return "captcha"
    return DEFAULT_LOGIN_REASON


def platform_start_url(platform: str, *, settings: Settings | None = None) -> str:
    """Chat / home URL opened in the crawl noVNC desktop for the platform."""
    settings = settings or get_settings()
    p = normalize_platform(platform)
    if p == PLATFORM_DOUBAO:
        from aperix_geo.services.providers.doubao_web import selectors as sel

        return (settings.doubao_chat_base_url or sel.CHAT_URL).strip() or sel.CHAT_URL
    # Placeholders until DeepSeek / Qianwen web crawl ships.
    if p == PLATFORM_DEEPSEEK:
        return "https://chat.deepseek.com/"
    if p == PLATFORM_QIANWEN:
        return "https://www.tongyi.com/"
    return ""
