"""Single-flight / request coalescing (Redis NX + in-process mutex)."""

from __future__ import annotations

import logging
import threading
import time
from collections import OrderedDict
from collections.abc import Callable
from typing import TypeVar

from aperix_geo.utils.cache.redis_kv import redis_delete, redis_set_nx

logger = logging.getLogger(__name__)

_LOCK_TTL_S = 120
_POLL_INTERVAL_S = 0.12
_MAX_LOCAL_LOCKS = 512

_local_guard = threading.Lock()
_local_locks: OrderedDict[str, threading.Lock] = OrderedDict()

T = TypeVar("T")


def _local_lock(key_digest: str) -> threading.Lock:
    with _local_guard:
        lock = _local_locks.get(key_digest)
        if lock is not None:
            _local_locks.move_to_end(key_digest)
            return lock
        lock = threading.Lock()
        _local_locks[key_digest] = lock
        while len(_local_locks) > _MAX_LOCAL_LOCKS:
            _local_locks.popitem(last=False)
        return lock


def run_single_flight(
    key_digest: str,
    *,
    wait_s: float,
    read_cache: Callable[[], T | None],
    fetch: Callable[[], T],
    lock_prefix: str,
) -> T:
    """Only one caller fetches; peers wait and re-read cache."""
    with _local_lock(key_digest):
        cached = read_cache()
        if cached is not None:
            return cached

        lock_key = f"{lock_prefix}{key_digest}"
        acquired = redis_set_nx(lock_key, ttl_s=_LOCK_TTL_S)
        if not acquired:
            deadline = time.time() + max(1.0, wait_s)
            while time.time() < deadline:
                cached = read_cache()
                if cached is not None:
                    return cached
                time.sleep(_POLL_INTERVAL_S)
            logger.debug("single-flight 等待超时，自行执行 %s", key_digest[:12])

        try:
            cached = read_cache()
            if cached is not None:
                return cached
            return fetch()
        finally:
            if acquired:
                redis_delete(lock_key)
