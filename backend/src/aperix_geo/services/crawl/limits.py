"""Per-domain page crawl limits: minute quota and in-flight concurrency."""

from __future__ import annotations

import time
from collections.abc import Iterator
from contextlib import contextmanager

from aperix_geo.config import get_settings
from aperix_geo.utils.cache.redis_kv import shared_redis_client
from aperix_geo.utils.domains import registrable_domain


class CrawlRateLimitError(RuntimeError):
    """Domain crawl quota or in-flight concurrency exceeded."""


def normalize_crawl_domain(host_or_url: str) -> str:
    text = (host_or_url or "").strip().lower()
    if not text:
        return ""
    if "://" in text or text.startswith("//"):
        from aperix_geo.utils.url import hostname_from_url

        host = hostname_from_url(text if not text.startswith("//") else f"https:{text}")
    else:
        host = text.split("/", 1)[0]
    if not host:
        return ""
    return registrable_domain(host) or host


def _minute_key(domain: str) -> str:
    return f"aperix:crawl_rl:{domain}:{int(time.time() // 60)}"


def _inflight_key(domain: str) -> str:
    return f"aperix:crawl_inflight:{domain}"


def _try_acquire_minute_quota(client, *, domain: str, limit_per_minute: int) -> None:
    if limit_per_minute <= 0:
        return
    mkey = _minute_key(domain)
    count = client.incr(mkey)
    if count == 1:
        client.expire(mkey, 120)
    if count > limit_per_minute:
        client.decr(mkey)
        raise CrawlRateLimitError(
            f"Crawl rate limit exceeded for {domain}; retry scheduled.",
        )


def _try_acquire_inflight_slot(client, *, domain: str, max_inflight: int, ttl_s: int) -> None:
    if max_inflight <= 0:
        return
    key = _inflight_key(domain)
    count = client.incr(key)
    if count == 1 or client.ttl(key) in (-1, -2):
        client.expire(key, ttl_s)
    if count > max_inflight:
        client.decr(key)
        raise CrawlRateLimitError(
            f"Crawl in-flight limit exceeded for {domain}; retry scheduled.",
        )


def _release_inflight_slot(client, *, domain: str) -> None:
    key = _inflight_key(domain)
    remaining = client.decr(key)
    if remaining <= 0:
        client.delete(key)


@contextmanager
def page_crawl_slot(host_or_url: str) -> Iterator[str]:
    """Acquire domain minute quota + in-flight slot before a live page fetch."""
    settings = get_settings()
    domain = normalize_crawl_domain(host_or_url)
    if not domain:
        yield ""
        return

    limits_disabled = (
        settings.page_crawl_domain_limit_per_minute <= 0
        and settings.page_crawl_domain_max_inflight <= 0
    )
    if limits_disabled:
        yield domain
        return

    client = shared_redis_client()
    if client is None:
        yield domain
        return

    deadline = time.monotonic() + settings.page_crawl_domain_limit_wait_s
    last_error: CrawlRateLimitError | None = None
    while True:
        try:
            _try_acquire_minute_quota(
                client,
                domain=domain,
                limit_per_minute=settings.page_crawl_domain_limit_per_minute,
            )
            _try_acquire_inflight_slot(
                client,
                domain=domain,
                max_inflight=settings.page_crawl_domain_max_inflight,
                ttl_s=settings.page_crawl_domain_inflight_ttl_s,
            )
            break
        except CrawlRateLimitError as exc:
            last_error = exc
            if time.monotonic() >= deadline:
                raise last_error from None
            time.sleep(0.25)

    try:
        yield domain
    finally:
        _release_inflight_slot(client, domain=domain)
