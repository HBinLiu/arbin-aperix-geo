"""Redis cache for LLM chat results — one provider call per response across retries."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from aperix_geo.config import get_settings
from aperix_geo.services.providers.result import SamplingChatResult
from aperix_geo.utils.cache.redis_kv import redis_delete, redis_get_json, redis_set_json_exat
from aperix_geo.utils.cache.ttl import expires_at_from_ttl


def _cache_key(response_id: UUID) -> str:
    return f"aperix:sampling:llm_result:v1:{response_id}"


def _to_payload(result: SamplingChatResult) -> dict[str, Any]:
    ttl_s = get_settings().sampling_llm_result_cache_ttl_s
    return {
        "text": result.text,
        "usage": result.usage,
        "latency_ms": result.latency_ms,
        "source_urls": list(result.source_urls),
        "web_search_mode": result.web_search_mode,
        "expires_at": expires_at_from_ttl(ttl_s),
    }


def _from_payload(payload: dict[str, Any]) -> SamplingChatResult:
    return SamplingChatResult(
        text=str(payload.get("text") or ""),
        usage=dict(payload.get("usage") or {}),
        latency_ms=int(payload.get("latency_ms") or 0),
        source_urls=tuple(str(u) for u in (payload.get("source_urls") or []) if str(u).strip()),
        web_search_mode=str(payload.get("web_search_mode") or "none"),
    )


def load_cached_llm_result(response_id: UUID) -> SamplingChatResult | None:
    payload = redis_get_json(_cache_key(response_id))
    if payload is None:
        return None
    return _from_payload(payload)


def save_cached_llm_result(response_id: UUID, result: SamplingChatResult) -> None:
    payload = _to_payload(result)
    expires_at = int(payload["expires_at"])
    redis_set_json_exat(_cache_key(response_id), payload, expires_at=expires_at)


def clear_cached_llm_result(response_id: UUID) -> None:
    redis_delete(_cache_key(response_id))
