"""Per-provider LLM rate limiting for sampling workers."""

from __future__ import annotations

import time

from aperix_geo.services.sampling.llm import rate_limit_for_platform
from aperix_geo.utils.cache.redis_kv import shared_redis_client


class SamplingRateLimitError(RuntimeError):
    """Provider minute quota exceeded; caller may retry later."""


def check_llm_rate_limit(platform: str) -> None:
    """Raise SamplingRateLimitError when the provider minute quota is exceeded."""
    provider, limit_per_minute = rate_limit_for_platform(platform)
    client = shared_redis_client()
    if client is None:
        return
    mkey = f"aperix:llm_rl:{provider}:{int(time.time() // 60)}"
    count = client.incr(mkey)
    if count == 1:
        client.expire(mkey, 120)
    if count > limit_per_minute:
        raise SamplingRateLimitError(
            f"LLM rate limit exceeded for {provider}; retry scheduled.",
        )
