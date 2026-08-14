"""Per-platform Redis capacity slots for account-pool crawl workers.

Slots cap concurrent crawl executions across processes. TTL matches account lease
so crashed workers cannot leak capacity forever.
"""

from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Iterator

from sqlalchemy.orm import Session

from aperix_geo.config import Settings, get_settings
from aperix_geo.services.crawl_accounts.pool import (
    account_pool_capacity_snapshot,
    effective_account_lease_ttl_s,
)
from aperix_geo.services.crawl_accounts.platforms import normalize_platform
from aperix_geo.utils.cache.redis_kv import shared_redis_client

logger = logging.getLogger(__name__)

_ACQUIRE_SCRIPT = """
local key = KEYS[1]
local max = tonumber(ARGV[1])
local ttl = tonumber(ARGV[2])
if max <= 0 then return 0 end
local current = tonumber(redis.call('GET', key) or '0')
if current >= max then return 0 end
local new = redis.call('INCR', key)
redis.call('EXPIRE', key, ttl)
if new > max then
  redis.call('DECR', key)
  return 0
end
return 1
"""


class CrawlCapacityBusy(RuntimeError):
    """No crawl capacity slot right now; caller should requeue, never API-fallback."""


class CrawlPoolEmpty(RuntimeError):
    """No usable fresh active accounts (not merely leased); may API-fallback if mode allows."""


def _slot_key(platform: str) -> str:
    return f"aperix:crawl:slots:{normalize_platform(platform)}"


def _slot_ttl_s(settings: Settings) -> int:
    return max(60, effective_account_lease_ttl_s(settings))


def platform_crawl_capacity(
    db: Session,
    platform: str,
    *,
    settings: Settings | None = None,
) -> int:
    """Acquirable accounts (fresh active, not leased)."""
    settings = settings or get_settings()
    snap = account_pool_capacity_snapshot(
        db, platform=normalize_platform(platform), settings=settings
    )
    return int(snap["free"])


def platform_crawl_pool_total(
    db: Session,
    platform: str,
    *,
    settings: Settings | None = None,
) -> int:
    settings = settings or get_settings()
    snap = account_pool_capacity_snapshot(
        db, platform=normalize_platform(platform), settings=settings
    )
    return int(snap["total"])


def try_acquire_crawl_slot(
    platform: str,
    *,
    capacity: int,
    settings: Settings | None = None,
) -> bool:
    settings = settings or get_settings()
    client = shared_redis_client()
    if client is None:
        # Without Redis, rely on worker concurrency + DB lease only.
        return capacity > 0
    if capacity <= 0:
        return False
    ttl = _slot_ttl_s(settings)
    key = _slot_key(platform)
    try:
        result = client.eval(_ACQUIRE_SCRIPT, 1, key, capacity, ttl)
        return int(result) == 1
    except Exception:
        logger.warning("crawl capacity acquire failed platform=%s", platform, exc_info=True)
        return capacity > 0


def release_crawl_slot(platform: str, *, settings: Settings | None = None) -> None:
    settings = settings or get_settings()
    client = shared_redis_client()
    if client is None:
        return
    key = _slot_key(platform)
    ttl = _slot_ttl_s(settings)
    try:
        value = int(client.decr(key))
        if value < 0:
            client.set(key, "0", ex=ttl)
        else:
            client.expire(key, ttl)
    except Exception:
        logger.debug("crawl capacity release failed platform=%s", platform, exc_info=True)


@contextmanager
def crawl_capacity_slot(
    db: Session,
    platform: str,
    *,
    settings: Settings | None = None,
) -> Iterator[None]:
    """Acquire a cross-process crawl slot or raise Busy/Empty."""
    settings = settings or get_settings()
    plat = normalize_platform(platform)
    snap = account_pool_capacity_snapshot(db, platform=plat, settings=settings)
    total = int(snap["total"])
    free = int(snap["free"])
    if total <= 0:
        raise CrawlPoolEmpty(f"no usable crawl accounts for platform={plat}")
    if free <= 0:
        raise CrawlCapacityBusy(f"crawl accounts leased platform={plat}")
    # Ceiling = total fresh actives so leased peers still count toward worker budget.
    ceiling = max(total, 1)
    if not try_acquire_crawl_slot(plat, capacity=ceiling, settings=settings):
        raise CrawlCapacityBusy(f"crawl slots busy platform={plat} capacity={ceiling}")
    try:
        yield
    finally:
        release_crawl_slot(plat, settings=settings)
