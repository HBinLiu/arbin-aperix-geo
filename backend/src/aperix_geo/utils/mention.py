"""Mention rank helpers (1-based rank in LLM reply; 0 = unset in DB)."""

from __future__ import annotations

NO_MENTION_RANK = 0


def has_mention_rank(rank: int | None) -> bool:
    if rank is None:
        return False
    return int(rank) > 0


def persist_mention_rank(rank: int | None) -> int:
    if rank is None or rank <= 0:
        return NO_MENTION_RANK
    return int(rank)


def api_mention_rank(rank: int | None) -> int | None:
    """Map stored rank to API null when unset."""
    if rank is None:
        return None
    value = int(rank)
    return value if has_mention_rank(value) else None
