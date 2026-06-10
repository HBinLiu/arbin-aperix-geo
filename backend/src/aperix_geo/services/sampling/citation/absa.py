"""Response-level ABSA on sampling AI output."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from aperix_geo.services.providers import LLMProviderError, chat_completion
from aperix_geo.services.providers.prompts import (
    CITATION_RESPONSE_ABSA_SYSTEM,
    citation_response_absa_user_content,
)
from aperix_geo.services.sampling.citation.cache.response_absa import (
    get_response_absa_cached,
    response_absa_cache_digest,
    set_response_absa_cached,
)
from aperix_geo.utils.cache import run_single_flight
from aperix_geo.utils.json import extract_json_object

logger = logging.getLogger(__name__)


def _brand_entry(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        return {"mentioned": False, "score": None, "framing_tags": [], "evidence": ""}
    mentioned = bool(raw.get("mentioned"))
    score = raw.get("score")
    try:
        score_val = float(score) if score is not None else None
    except (TypeError, ValueError):
        score_val = None
    tags = raw.get("framing_tags")
    framing_tags = [str(t).strip() for t in tags if str(t).strip()] if isinstance(tags, list) else []
    evidence = str(raw.get("evidence") or "").strip()
    return {
        "mentioned": mentioned,
        "score": score_val,
        "framing_tags": framing_tags,
        "evidence": evidence,
    }


def normalize_response_absa(
    data: dict[str, Any],
    *,
    own_brand: str,
    competitors: list[str],
) -> dict[str, Any]:
    brands_raw = data.get("brands_sentiment_absa") if isinstance(data.get("brands_sentiment_absa"), dict) else {}
    brands: dict[str, dict[str, Any]] = {}
    for name in [own_brand, *competitors]:
        if not name:
            continue
        brands[name] = _brand_entry(brands_raw.get(name))
    return {
        "analysis_timestamp": str(data.get("analysis_timestamp") or datetime.now(UTC).isoformat()),
        "brands_sentiment_absa": brands,
        "analysis_source": "llm",
    }


def _empty_response_absa(*, reason: str) -> dict[str, Any]:
    return {
        "analysis_timestamp": datetime.now(UTC).isoformat(),
        "brands_sentiment_absa": {},
        "analysis_source": "failed",
        "failure_reason": reason,
    }


def analyze_citation_response_absa(
    raw_text: str,
    *,
    own_brand: str,
    competitors: list[str],
    cache_ttl_s: int = 0,
) -> dict[str, Any]:
    """ABSA on the sampling AI response text (once per LLM response)."""
    if not own_brand.strip():
        return _empty_response_absa(reason="missing own brand")
    if not raw_text.strip():
        return _empty_response_absa(reason="empty ai response")

    def _read_cache() -> dict[str, Any] | None:
        return get_response_absa_cached(
            raw_text=raw_text,
            own_brand=own_brand,
            competitors=competitors,
            ttl_s=cache_ttl_s,
        )

    cached = _read_cache()
    if cached is not None:
        return cached

    def _fetch() -> dict[str, Any]:
        messages = [
            {"role": "system", "content": CITATION_RESPONSE_ABSA_SYSTEM},
            {
                "role": "user",
                "content": citation_response_absa_user_content(
                    raw_text=raw_text,
                    own_brand=own_brand,
                    competitors=competitors,
                ),
            },
        ]
        try:
            text, _, _ = chat_completion(messages, temperature=0.0, json_mode=True)
            data = extract_json_object(text)
            if not isinstance(data, dict):
                raise ValueError("response absa is not an object")
            result = normalize_response_absa(data, own_brand=own_brand, competitors=competitors)
            set_response_absa_cached(
                raw_text=raw_text,
                own_brand=own_brand,
                competitors=competitors,
                result=result,
                ttl_s=cache_ttl_s,
            )
            return result
        except (LLMProviderError, TypeError, ValueError, KeyError) as exc:
            logger.warning("Citation response ABSA failed: %s", exc)
            return _empty_response_absa(reason=str(exc)[:500])

    if cache_ttl_s <= 0:
        return _fetch()

    digest = response_absa_cache_digest(
        raw_text=raw_text,
        own_brand=own_brand,
        competitors=competitors,
    )
    return run_single_flight(
        digest,
        wait_s=120.0,
        read_cache=_read_cache,
        fetch=_fetch,
        lock_prefix="aperix:response_absa:lock:",
    )
