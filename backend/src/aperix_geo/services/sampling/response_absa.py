"""Response-level ABSA on sampling LLM output."""

from __future__ import annotations

import logging
import threading
from typing import Any

from aperix_geo.services.brand.keys import configured_brand_keys
from aperix_geo.services.brand.resolve import normalize_brand_key
from aperix_geo.services.providers import LLMProviderError, chat_completion
from aperix_geo.services.providers.prompts import (
    CITATION_RESPONSE_ABSA_SYSTEM,
    citation_response_absa_user_content,
)
from aperix_geo.services.sampling.cache.absa import (
    get_response_absa_cached,
    response_absa_cache_digest,
    set_response_absa_cached,
)
from aperix_geo.services.sampling.enumeration import (
    is_plausible_commercial_span,
    normalize_mention_span,
)
from aperix_geo.services.sampling.enumeration import merge_mention_candidates
from aperix_geo.services.sampling.mentions import discover_response_mentions
from aperix_geo.services.sampling.signal_draft import EntitySignalDraft
from aperix_geo.utils.cache import SingleFlightWaitTimeout, run_single_flight
from aperix_geo.utils.json import extract_json_object

logger = logging.getLogger(__name__)


def response_absa_needed(
    *,
    llm_configured: bool,
    text: str,
    entity_signals: list[EntitySignalDraft],
) -> bool:
    """Run ABSA when own/competitor brands are mentioned in the response text."""
    if not llm_configured or not text.strip():
        return False
    return any(
        draft.mentioned and draft.entity_kind in ("own", "competitor")
        for draft in entity_signals
    )


def _brand_entry(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        return {"mentioned": False, "score": None, "evidence": ""}
    mentioned = bool(raw.get("mentioned"))
    score = raw.get("score")
    try:
        score_val = float(score) if score is not None else None
    except (TypeError, ValueError):
        score_val = None
    evidence = str(raw.get("evidence") or "").strip()
    return {
        "mentioned": mentioned,
        "score": score_val,
        "evidence": evidence,
    }


def normalize_response_absa(
    data: dict[str, Any],
    *,
    own_brand: str,
    competitors: list[str],
    excluded_keys: set[str] | None = None,
) -> dict[str, Any]:
    brands_raw = data.get("brands_sentiment_absa") if isinstance(data.get("brands_sentiment_absa"), dict) else {}
    brands: dict[str, dict[str, Any]] = {}
    closed_names = list(dict.fromkeys([name for name in competitors if str(name).strip()]))
    if own_brand.strip() and own_brand not in closed_names:
        closed_names.insert(0, own_brand.strip())
    for name in closed_names:
        brands[name] = _brand_entry(brands_raw.get(name))

    if excluded_keys is None:
        excluded_keys = configured_brand_keys(
            own_brand=own_brand,
            competitor_brand_names=competitors,
        )

    other_brands: dict[str, dict[str, Any]] = {}
    others_raw = data.get("other_brands_sentiment_absa")
    if isinstance(others_raw, dict):
        for name, entry in others_raw.items():
            label = normalize_mention_span(str(name or ""))
            if not label or normalize_brand_key(label) in excluded_keys:
                continue
            if not is_plausible_commercial_span(label):
                continue
            other_brands[label] = _brand_entry(entry)

    return {
        "brands_sentiment_absa": brands,
        "other_brands_sentiment_absa": other_brands,
        "analysis_source": "llm",
    }


def _empty_response_absa(*, reason: str) -> dict[str, Any]:
    return {
        "brands_sentiment_absa": {},
        "other_brands_sentiment_absa": {},
        "analysis_source": "failed",
        "failure_reason": reason,
    }


def _attach_mention_candidates(result: dict[str, Any], mention_candidates: list[str]) -> dict[str, Any]:
    payload = dict(result)
    payload["mention_candidates"] = list(mention_candidates)
    return payload


def analyze_response_absa(
    raw_text: str,
    *,
    own_brand: str,
    competitors: list[str],
    own_brand_names: list[str] | None = None,
    competitor_brand_names: list[str] | None = None,
    excluded_keys: set[str] | None = None,
    cache_ttl_s: int = 0,
    mention_discovery_enabled: bool = False,
    mention_discovery_cache_ttl_s: int = 0,
    track_context: str = "",
) -> tuple[dict[str, Any], bool]:
    """ABSA on the sampling LLM response text (once per LLM response).

    When mention discovery is enabled, runs a high-recall discovery pass first and
    merges spans with rule-based enumeration before ABSA.

    Returns ``(result, live_call)``; cache hits are not billed.
    """
    if not own_brand.strip():
        return _empty_response_absa(reason="missing own brand"), False
    if not raw_text.strip():
        return _empty_response_absa(reason="empty ai response"), False

    closed_brand_names = list(competitors)
    if own_brand_names or competitor_brand_names:
        closed_brand_names = list(
            dict.fromkeys([*(own_brand_names or []), *(competitor_brand_names or [])])
        )

    if excluded_keys is None:
        excluded_keys = configured_brand_keys(
            own_brand=own_brand,
            competitor_brand_names=closed_brand_names,
        )

    discovery_spans: list[str] = []
    discovery_live = False
    if mention_discovery_enabled:
        discovery_spans, discovery_live = discover_response_mentions(
            raw_text,
            cache_ttl_s=mention_discovery_cache_ttl_s,
            track_context=track_context,
        )
    mention_candidates = merge_mention_candidates(raw_text, discovery_spans)

    def _read_cache() -> dict[str, Any] | None:
        cached = get_response_absa_cached(
            raw_text=raw_text,
            own_brand=own_brand,
            competitors=closed_brand_names,
            excluded_keys=excluded_keys,
            mention_candidates=mention_candidates,
            track_context=track_context,
            ttl_s=cache_ttl_s,
        )
        if cached is None:
            return None
        return _attach_mention_candidates(cached, mention_candidates)

    cached = _read_cache()
    if cached is not None:
        return cached, discovery_live

    live_flag = threading.local()

    def _fetch() -> dict[str, Any]:
        messages = [
            {"role": "system", "content": CITATION_RESPONSE_ABSA_SYSTEM},
            {
                "role": "user",
                "content": citation_response_absa_user_content(
                    raw_text=raw_text,
                    own_brand=own_brand,
                    own_brand_names=own_brand_names,
                    competitor_brand_names=competitor_brand_names,
                    competitors=closed_brand_names,
                    mention_candidates=mention_candidates,
                    track_context=track_context,
                ),
            },
        ]
        try:
            text, _, _ = chat_completion(messages, temperature=0.0, json_mode=True)
            live_flag.did = True
            data = extract_json_object(text)
            if not isinstance(data, dict):
                raise ValueError("response absa is not an object")
            result = normalize_response_absa(
                data,
                own_brand=own_brand,
                competitors=closed_brand_names,
                excluded_keys=excluded_keys,
            )
            result = _attach_mention_candidates(result, mention_candidates)
            set_response_absa_cached(
                raw_text=raw_text,
                own_brand=own_brand,
                competitors=closed_brand_names,
                excluded_keys=excluded_keys,
                mention_candidates=mention_candidates,
                track_context=track_context,
                result=result,
                ttl_s=cache_ttl_s,
            )
            return result
        except (LLMProviderError, TypeError, ValueError, KeyError) as exc:
            logger.warning("Response ABSA failed: %s", exc)
            return _empty_response_absa(reason=str(exc)[:500])

    if cache_ttl_s <= 0:
        return _fetch(), discovery_live or True

    digest = response_absa_cache_digest(
        raw_text=raw_text,
        own_brand=own_brand,
        competitors=closed_brand_names,
        excluded_keys=excluded_keys,
        mention_candidates=mention_candidates,
        track_context=track_context,
    )
    try:
        result = run_single_flight(
            digest,
            wait_s=120.0,
            read_cache=_read_cache,
            fetch=_fetch,
            lock_prefix="aperix:response_absa:lock:",
        )
        return result, discovery_live or bool(getattr(live_flag, "did", False))
    except SingleFlightWaitTimeout:
        cached = _read_cache()
        if cached is not None:
            return cached, discovery_live
        logger.warning("Response ABSA single-flight wait timeout")
        return _empty_response_absa(reason="absa single-flight wait timeout"), discovery_live
