"""Cache cross-validate scores to dedupe concurrent open-brand validation."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from aperix_geo.utils.cache import TieredJsonCache
from aperix_geo.utils.domains import registrable_domain

_STORE = TieredJsonCache(
    redis_prefix="aperix:cross_validate:score:v1:",
    l1_max_entries=256,
    strip_expires_on_read=True,
)

_DEFAULT_TTL_S = 86_400


def _cache_key(subject_id: UUID, domain: str) -> str:
    root = registrable_domain(domain) or domain.strip().lower()
    return f"{subject_id}:{root}"


def get_cross_validate_score_cached(
    *,
    subject_id: UUID,
    domain: str,
    ttl_s: int = _DEFAULT_TTL_S,
) -> dict[str, Any] | None:
    if ttl_s <= 0:
        return None
    payload = _STORE.get(
        _cache_key(subject_id, domain),
        default_ttl_s=ttl_s,
        is_valid=lambda data: data.get("score") is not None,
    )
    return payload if isinstance(payload, dict) else None


def set_cross_validate_score_cached(
    *,
    subject_id: UUID,
    domain: str,
    score: float,
    reason: str,
    ttl_s: int = _DEFAULT_TTL_S,
) -> None:
    if ttl_s <= 0:
        return
    _STORE.set(
        _cache_key(subject_id, domain),
        {"score": float(score), "reason": str(reason or "")[:500]},
        ttl_s=ttl_s,
    )


def clear_cross_validate_score_cache() -> None:
    _STORE.clear()
