"""Shared TTL helpers: absolute expires_at as cache authority."""

from __future__ import annotations

import time
from typing import Any


def expires_at_from_ttl(ttl_s: int) -> int:
    return int(time.time()) + max(1, ttl_s)


def is_payload_expired(payload: dict[str, Any], *, now: float | None = None) -> bool:
    now = time.time() if now is None else now
    expires_at = payload.get("expires_at")
    if isinstance(expires_at, (int, float)):
        return now >= float(expires_at)
    return False


def remaining_ttl_s(payload: dict[str, Any], *, now: float | None = None) -> int:
    now = time.time() if now is None else now
    expires_at = payload.get("expires_at")
    if not isinstance(expires_at, (int, float)):
        return 0
    return max(0, int(float(expires_at) - now))
