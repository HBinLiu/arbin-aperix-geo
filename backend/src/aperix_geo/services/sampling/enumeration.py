"""Extract named spans from list-like patterns in AI response text (enumeration hints)."""

from __future__ import annotations

import re

_ENUM_SEP = re.compile(r"[、,/;；|]")
_PAREN = re.compile(r"[（(]([^）)]+)[）)]")
_TRAILING_ETC = re.compile(r"(?:等|等等|之类|etc\.?|…|\.\.\.)$", re.IGNORECASE)
_SLASH_RUN = re.compile(
    r"(?<![/\w])"
    r"([\u4e00-\u9fff\w][\u4e00-\u9fff\w·\-]{0,24}"
    r"(?:/[\u4e00-\u9fff\w][\u4e00-\u9fff\w·\-]{0,24})+)"
    r"(?![/\w])"
)
_NOISE = re.compile(r"^[\d\s·\-_.]+$")
_URL_SPAN = re.compile(r"https?://\S+", re.IGNORECASE)


def _text_without_urls(text: str) -> str:
    return _URL_SPAN.sub(" ", text)

_MIN_LEN = 2
_MAX_LEN = 48


def _normalize_item(raw: str) -> str:
    item = raw.strip().strip("\"'“”‘’")
    item = item.strip("*# ")
    item = _TRAILING_ETC.sub("", item).strip()
    return item


def _appears_in_text(item: str, text: str) -> bool:
    if not item or not text:
        return False
    if item.isascii():
        return item.lower() in text.lower()
    return item in text


def _is_valid_candidate(item: str, text: str) -> bool:
    if len(item) < _MIN_LEN or len(item) > _MAX_LEN:
        return False
    if _NOISE.match(item):
        return False
    if _URL_SPAN.search(item) or "://" in item or item.startswith("www."):
        return False
    if not _appears_in_text(item, text):
        return False
    return True


def _split_enum_chunk(chunk: str) -> list[str]:
    parts = _ENUM_SEP.split(chunk)
    items: list[str] = []
    for part in parts:
        item = _normalize_item(part)
        if item:
            items.append(item)
    return items


def _extract_from_parentheses(text: str) -> list[str]:
    items: list[str] = []
    for match in _PAREN.finditer(text):
        inner = match.group(1).strip()
        if not inner or "://" in inner or "www." in inner.lower():
            continue
        if not _ENUM_SEP.search(inner):
            continue
        items.extend(_split_enum_chunk(inner))
    return items


def _extract_slash_runs(text: str) -> list[str]:
    items: list[str] = []
    for match in _SLASH_RUN.finditer(_text_without_urls(text)):
        chunk = match.group(1)
        items.extend(_split_enum_chunk(chunk))
    return items


def extract_enumerated_spans(text: str) -> list[str]:
    """Return deduplicated spans from parenthetical or slash-separated enumerations."""
    if not text.strip():
        return []

    ordered: list[str] = []
    seen: set[str] = set()

    def add_many(raw_items: list[str]) -> None:
        for item in raw_items:
            key = item.casefold() if item.isascii() else item
            if key in seen:
                continue
            if not _is_valid_candidate(item, text):
                continue
            seen.add(key)
            ordered.append(item)

    add_many(_extract_from_parentheses(text))
    add_many(_extract_slash_runs(text))
    return ordered


def filter_mention_spans(spans: list[str], text: str) -> list[str]:
    """Keep spans that literally appear in text; dedupe preserving order."""
    ordered: list[str] = []
    seen: set[str] = set()
    for raw in spans:
        item = _normalize_item(str(raw or ""))
        if not item:
            continue
        key = item.casefold() if item.isascii() else item
        if key in seen:
            continue
        if not _is_valid_candidate(item, text):
            continue
        seen.add(key)
        ordered.append(item)
    return ordered


def merge_mention_candidates(text: str, *extra_lists: list[str]) -> list[str]:
    """Merge rule-based enumeration spans with optional discovery spans."""
    ordered: list[str] = []
    seen: set[str] = set()

    def add_many(items: list[str]) -> None:
        for item in items:
            key = item.casefold() if item.isascii() else item
            if key in seen:
                continue
            seen.add(key)
            ordered.append(item)

    add_many(extract_enumerated_spans(text))
    for extra in extra_lists:
        if extra:
            add_many(filter_mention_spans(extra, text))
    return ordered
