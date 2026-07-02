"""Plain-text normalization, truncation, hashing, and markdown helpers."""

from __future__ import annotations

import hashlib
import re
from collections import Counter


def normalize_whitespace(text: str) -> str:
    return " ".join((text or "").strip().split())


def reply_text(raw_text: str) -> str:
    """Collapse newlines for single-line reply previews in analysis views."""
    return (raw_text or "").replace("\n", " ").strip()


def truncate_text(text: str, max_chars: int, *, suffix: str = "\n\n…(内容已截断)") -> str:
    if len(text) <= max_chars:
        return text
    return text[: max_chars - len(suffix)].rstrip() + suffix


def prompt_text_hash(text: str) -> str:
    """SHA-256 hex digest of normalized prompt text (for dedup)."""
    normalized = normalize_whitespace(text)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def headings_from_markdown(markdown: str, *, limit: int = 4) -> str:
    headings: list[str] = []
    for line in markdown.splitlines():
        stripped = line.strip()
        if not stripped.startswith("#"):
            continue
        text = re.sub(r"^#+\s*", "", stripped).strip()
        if text:
            headings.append(text)
        if len(headings) >= limit:
            break
    return " | ".join(headings)


def mode_nonempty(values: list[str]) -> str:
    """Most common non-empty string; empty when none."""
    cleaned = [value.strip() for value in values if value and value.strip()]
    if not cleaned:
        return ""
    return Counter(cleaned).most_common(1)[0][0]


_TEMPLATE_PLACEHOLDER_RE = re.compile(
    r"\{\{[^}]+\}\}|%\{[^}]+\}|%\([^)]+\)[sd]|\$\{[^}]+\}"
)


def is_template_title(title: str) -> bool:
    """True when title looks like an unresolved SSR/CSR template placeholder."""
    text = normalize_whitespace(title)
    if not text:
        return False
    return bool(_TEMPLATE_PLACEHOLDER_RE.search(text))


_GARBLED_MOJIBAKE_RE = re.compile(r"[\u0080-\u009f\u00c0-\u00ff]{3,}")


def _garbled_score(text: str) -> int:
    score = text.count("\ufffd")
    if _GARBLED_MOJIBAKE_RE.search(text):
        score += 4
    for ch in text:
        code = ord(ch)
        if 0x80 <= code <= 0x9F:
            score += 2
    return score


def repair_utf8_mojibake(text: str) -> str:
    """Recover UTF-8 Chinese titles that were decoded as Latin-1/Windows-1252."""
    if not text:
        return text
    try:
        repaired = text.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return text
    if _garbled_score(repaired) < _garbled_score(text):
        return repaired
    return text


def is_garbled_page_title(title: str) -> bool:
    text = normalize_whitespace(title)
    if not text:
        return True
    if "\ufffd" in text:
        return True
    return _garbled_score(text) >= max(3, len(text) // 6)


def sanitize_page_title(title: str) -> str:
    cleaned = normalize_whitespace(title or "")
    if not cleaned or is_template_title(cleaned):
        return ""
    cleaned = repair_utf8_mojibake(cleaned)
    if is_garbled_page_title(cleaned):
        return ""
    return cleaned


def coalesce_page_title(title: str, *fallbacks: str, url: str = "") -> str:
    """Return the first non-empty, non-template, non-garbled title; else url."""
    for candidate in (title, *fallbacks):
        cleaned = sanitize_page_title(candidate or "")
        if cleaned:
            return cleaned
    return normalize_whitespace(url)
