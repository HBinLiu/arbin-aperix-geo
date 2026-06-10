"""Plain-text normalization, truncation, hashing, and markdown helpers."""

from __future__ import annotations

import hashlib
import re
from collections import Counter


def normalize_whitespace(text: str) -> str:
    return " ".join((text or "").strip().split())


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
