"""Per-provider LLM limits: minute quota and in-flight concurrency."""

from __future__ import annotations

import time
from collections.abc import Iterator
from contextlib import contextmanager

from aperix_geo.config import get_settings
from aperix_geo.services.sampling.llm import rate_limit_for_platform
from aperix_geo.utils.cache.redis_kv import shared_redis_client


class SamplingRateLimitError(RuntimeError):
    """Provider quota or in-flight concurrency exceeded; caller may retry later."""


def provider_limits_for_platform(platform: str) -> tuple[str, int, int]:
    """Return ``(provider, limit_per_minute, max_inflight)`` for a sampling platform."""
    settings = get_settings()
    provider, limit_per_minute = rate_limit_for_platform(platform, settings=settings)
    return provider, limit_per_minute, settings.sampling_llm_max_inflight


def _minute_key(provider: str) -> str:
    return f"aperix:llm_rl:{provider}:{int(time.time() // 60)}"


def _inflight_key(provider: str) -> str:
    return f"aperix:llm_inflight:{provider}"


def _require_redis():
    client = shared_redis_client()
    if client is None:
        raise SamplingRateLimitError("Redis unavailable; cannot enforce LLM rate limits")
    return client


def _acquire_minute_quota(client, *, provider: str, limit_per_minute: int) -> None:
    mkey = _minute_key(provider)
    count = client.incr(mkey)
    if count == 1:
        client.expire(mkey, 120)
    if count > limit_per_minute:
        raise SamplingRateLimitError(
            f"LLM rate limit exceeded for {provider}; retry scheduled.",
        )


def _acquire_inflight_slot(client, *, provider: str, max_inflight: int, ttl_s: int) -> None:
    key = _inflight_key(provider)
    count = client.incr(key)
    if count == 1 or client.ttl(key) in (-1, -2):
        client.expire(key, ttl_s)
    if count > max_inflight:
        client.decr(key)
        raise SamplingRateLimitError(
            f"LLM in-flight limit exceeded for {provider}; retry scheduled.",
        )


def _release_inflight_slot(client, *, provider: str) -> None:
    key = _inflight_key(provider)
    remaining = client.decr(key)
    if remaining <= 0:
        client.delete(key)


@contextmanager
def llm_sampling_slot(platform: str) -> Iterator[str]:
    """Acquire minute quota + in-flight slot before a live provider HTTP call."""
    provider, limit_per_minute, max_inflight = provider_limits_for_platform(platform)
    settings = get_settings()
    client = _require_redis()
    _acquire_minute_quota(client, provider=provider, limit_per_minute=limit_per_minute)
    _acquire_inflight_slot(
        client,
        provider=provider,
        max_inflight=max_inflight,
        ttl_s=settings.sampling_llm_inflight_ttl_s,
    )
    try:
        yield provider
    finally:
        _release_inflight_slot(client, provider=provider)
