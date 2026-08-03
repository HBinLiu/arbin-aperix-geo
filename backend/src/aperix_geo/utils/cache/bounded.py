"""Bounded in-process TTL cache (LRU eviction)."""

from __future__ import annotations

import threading
import time
from collections import OrderedDict
from typing import Any


class BoundedTTLCache:
    """Thread-safe LRU cache with wall-clock expiry."""

    __slots__ = ("_data", "_lock", "_maxsize")

    def __init__(self, maxsize: int) -> None:
        self._maxsize = max(1, maxsize)
        self._data: OrderedDict[str, tuple[int, Any]] = OrderedDict()
        self._lock = threading.Lock()

    def get(self, key: str) -> Any | None:
        now = time.time()
        with self._lock:
            entry = self._data.get(key)
            if entry is None:
                return None
            expires_at, value = entry
            if now >= expires_at:
                del self._data[key]
                return None
            self._data.move_to_end(key)
            return value

    def set(self, key: str, value: Any, *, expires_at: int) -> None:
        if time.time() >= expires_at:
            return
        with self._lock:
            self._data[key] = (expires_at, value)
            self._data.move_to_end(key)
            while len(self._data) > self._maxsize:
                self._data.popitem(last=False)

    def clear(self) -> None:
        with self._lock:
            self._data.clear()

    def clear_prefix(self, prefix: str) -> int:
        """Drop L1 entries whose key starts with ``prefix``. Returns removed count."""
        if not prefix:
            return 0
        with self._lock:
            keys = [key for key in self._data if key.startswith(prefix)]
            for key in keys:
                del self._data[key]
            return len(keys)
