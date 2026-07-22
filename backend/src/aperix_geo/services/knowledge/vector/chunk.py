"""Plain-text chunking for knowledge sources."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TextChunk:
    text: str
    char_start: int
    char_end: int
    chunk_index: int


def chunk_text(
    text: str,
    *,
    chunk_size: int = 500,
    overlap: int = 64,
    max_chunks: int = 500,
) -> list[TextChunk]:
    """Split text into overlapping chunks (character-based, Chinese-friendly)."""
    normalized = text.replace("\r\n", "\n").strip()
    if not normalized:
        return []
    if chunk_size < 1:
        raise ValueError("chunk_size must be >= 1")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be in [0, chunk_size)")

    spans = _split_spans(normalized, chunk_size=chunk_size, overlap=overlap, max_chunks=max_chunks)
    return [
        TextChunk(
            text=normalized[start:end],
            char_start=start,
            char_end=end,
            chunk_index=idx,
        )
        for idx, (start, end) in enumerate(spans)
    ]


def _split_spans(
    text: str,
    *,
    chunk_size: int,
    overlap: int,
    max_chunks: int,
) -> list[tuple[int, int]]:
    if len(text) <= chunk_size:
        return [(0, len(text))]

    spans: list[tuple[int, int]] = []
    start = 0
    while start < len(text) and len(spans) < max_chunks:
        end = min(start + chunk_size, len(text))
        if end < len(text):
            end = _refine_end(text, start, end)
        if end <= start:
            end = min(start + chunk_size, len(text))
        spans.append((start, end))
        if end >= len(text):
            break
        start = max(end - overlap, start + 1)

    return spans


def _refine_end(text: str, start: int, end: int) -> int:
    window = text[start:end]
    para = window.rfind("\n\n")
    if para > len(window) // 3:
        return start + para

    best = -1
    for mark in ("。", "！", "？", ".", "!", "?"):
        pos = window.rfind(mark)
        if pos > best:
            best = pos
    if best > len(window) // 3:
        return start + best + 1

    return end


def estimate_token_count(text: str) -> int:
    """Rough token estimate for billing reconciliation."""
    stripped = text.strip()
    if not stripped:
        return 0
    return max(1, len(stripped) // 2)
