"""LLM analysis for citation sources: response-level ABSA + per-URL page GEO."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from aperix_geo.utils.cache import run_single_flight
from aperix_geo.services.providers import LLMProviderError, chat_completion
from aperix_geo.services.providers.prompts import (
    CITATION_PAGE_GEO_BATCH_SYSTEM,
    CITATION_PAGE_GEO_SYSTEM,
    CITATION_RESPONSE_ABSA_SYSTEM,
    _page_geo_entry,
    citation_page_geo_batch_user_content,
    citation_page_geo_user_content,
    citation_response_absa_user_content,
)
from aperix_geo.services.sampling._absa_cache import (
    get_response_absa_cached,
    response_absa_cache_digest,
    set_response_absa_cached,
)
from aperix_geo.services.sampling._geo_cache import (
    get_page_geo_cached,
    page_geo_cache_digest,
    set_page_geo_cached,
)
from aperix_geo.services.sampling.citation_page import CitationPageMeta
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


def normalize_page_geo(data: dict[str, Any]) -> dict[str, Any]:
    domain_cls = data.get("domain_classification") if isinstance(data.get("domain_classification"), dict) else {}
    url_cls = data.get("url_classification") if isinstance(data.get("url_classification"), dict) else {}
    page_brands_raw = data.get("page_mentioned_brands")
    page_mentioned_brands: list[str] = []
    if isinstance(page_brands_raw, list):
        page_mentioned_brands = [str(name).strip() for name in page_brands_raw if str(name).strip()]
    return {
        "analysis_timestamp": str(data.get("analysis_timestamp") or datetime.now(UTC).isoformat()),
        "domain_classification": {
            "type": str(domain_cls.get("type") or domain_cls.get("detected_domain_type") or "").strip(),
            "reason": str(domain_cls.get("reason") or domain_cls.get("domain_reason") or "").strip(),
        },
        "url_classification": {
            "type": str(url_cls.get("type") or url_cls.get("detected_type") or "").strip(),
            "reason": str(url_cls.get("reason") or url_cls.get("classification_reason") or "").strip(),
        },
        "page_mentioned_brands": page_mentioned_brands,
        "analysis_source": "llm",
    }


def page_mentioned_brand_names(analysis: dict[str, Any] | None) -> list[str]:
    """Brand names mentioned on the citation source page (from page GEO analysis)."""
    if not isinstance(analysis, dict):
        return []
    brands = analysis.get("page_mentioned_brands")
    if isinstance(brands, list):
        return [str(name).strip() for name in brands if str(name).strip()]
    return []


def ai_mentioned_brand_names(response_absa: dict[str, Any] | None) -> list[str]:
    """Brand names mentioned in the sampling AI response (from response ABSA)."""
    if not isinstance(response_absa, dict):
        return []
    brands = response_absa.get("brands_sentiment_absa")
    if not isinstance(brands, dict):
        return []
    names: list[str] = []
    for name, entry in brands.items():
        label = str(name or "").strip()
        if label and isinstance(entry, dict) and entry.get("mentioned"):
            names.append(label)
    return names


def brand_names_match(names: list[str], mentioned: list[str]) -> bool:
    """Case-insensitive match between configured brand keys and mentioned list."""
    if not names or not mentioned:
        return False
    mentioned_keys = {m.strip().lower() for m in mentioned if m.strip()}
    return any(n.strip().lower() in mentioned_keys for n in names if n.strip())


def _empty_response_absa(*, reason: str) -> dict[str, Any]:
    return {
        "analysis_timestamp": datetime.now(UTC).isoformat(),
        "brands_sentiment_absa": {},
        "analysis_source": "failed",
        "failure_reason": reason,
    }


def _empty_page_geo(*, reason: str) -> dict[str, Any]:
    return {
        "analysis_timestamp": datetime.now(UTC).isoformat(),
        "domain_classification": {"type": "", "reason": reason},
        "url_classification": {"type": "", "reason": reason},
        "page_mentioned_brands": [],
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


def analyze_citation_page_geo(
    page: CitationPageMeta,
    *,
    own_brand: str,
    competitors: list[str],
    cache_ttl_s: int = 0,
) -> dict[str, Any]:
    """GEO classification + source-page brand mentions for one citation URL."""
    if not own_brand.strip():
        return _empty_page_geo(reason="missing own brand")

    def _read_cache() -> dict[str, Any] | None:
        return get_page_geo_cached(
            url=page.url,
            text_snippet=page.text_snippet,
            own_brand=own_brand,
            competitors=competitors,
            ttl_s=cache_ttl_s,
        )

    cached = _read_cache()
    if cached is not None:
        return cached

    def _fetch() -> dict[str, Any]:
        messages = [
            {"role": "system", "content": CITATION_PAGE_GEO_SYSTEM},
            {
                "role": "user",
                "content": citation_page_geo_user_content(
                    own_brand=own_brand,
                    competitors=competitors,
                    url=page.url,
                    domain=page.domain,
                    http_status=page.http_status,
                    title=page.title,
                    description=page.description,
                    headings_list=page.headings_list,
                    has_table=page.has_table,
                    has_code_block=page.has_code_block,
                    text_snippet=page.text_snippet,
                ),
            },
        ]
        try:
            text, _, _ = chat_completion(messages, temperature=0.0, json_mode=True)
            data = extract_json_object(text)
            if not isinstance(data, dict):
                raise ValueError("page geo is not an object")
            result = normalize_page_geo(data)
            set_page_geo_cached(
                url=page.url,
                text_snippet=page.text_snippet,
                own_brand=own_brand,
                competitors=competitors,
                result=result,
                ttl_s=cache_ttl_s,
            )
            return result
        except (LLMProviderError, TypeError, ValueError, KeyError) as exc:
            logger.warning("Citation page GEO failed for %s: %s", page.url, exc)
            return _empty_page_geo(reason=str(exc)[:500])

    if cache_ttl_s <= 0:
        return _fetch()

    digest = page_geo_cache_digest(
        url=page.url,
        text_snippet=page.text_snippet,
        own_brand=own_brand,
        competitors=competitors,
    )
    return run_single_flight(
        digest,
        wait_s=120.0,
        read_cache=_read_cache,
        fetch=_fetch,
        lock_prefix="aperix:page_geo:lock:",
    )


def _page_geo_batch_entries(pages: list[CitationPageMeta]) -> list[dict[str, object]]:
    return [
        _page_geo_entry(
            url=page.url,
            domain=page.domain,
            http_status=page.http_status,
            title=page.title,
            description=page.description,
            headings_list=page.headings_list,
            has_table=page.has_table,
            has_code_block=page.has_code_block,
            text_snippet=page.text_snippet,
        )
        for page in pages
    ]


def _analyze_citation_page_geo_batch(
    pages: list[CitationPageMeta],
    *,
    own_brand: str,
    competitors: list[str],
    cache_ttl_s: int,
) -> list[dict[str, Any]]:
    if not pages:
        return []
    if len(pages) == 1:
        return [
            analyze_citation_page_geo(
                pages[0],
                own_brand=own_brand,
                competitors=competitors,
                cache_ttl_s=cache_ttl_s,
            ),
        ]

    messages = [
        {"role": "system", "content": CITATION_PAGE_GEO_BATCH_SYSTEM},
        {
            "role": "user",
            "content": citation_page_geo_batch_user_content(
                own_brand=own_brand,
                competitors=competitors,
                pages=_page_geo_batch_entries(pages),
            ),
        },
    ]
    try:
        text, _, _ = chat_completion(
            messages,
            temperature=0.0,
            json_mode=True,
        )
        data = extract_json_object(text)
        if not isinstance(data, dict):
            raise ValueError("batch page geo is not an object")
        rows = data.get("pages")
        if not isinstance(rows, list):
            raise ValueError("batch page geo missing pages array")

        by_url: dict[str, dict[str, Any]] = {}
        for row in rows:
            if not isinstance(row, dict):
                continue
            url_key = str(row.get("url") or "").strip()
            if url_key:
                by_url[url_key] = normalize_page_geo(row)

        out: list[dict[str, Any]] = []
        for page in pages:
            hit = by_url.get(page.url.strip())
            if hit is None:
                raise ValueError(f"batch page geo missing url {page.url}")
            out.append(hit)
        return out
    except (LLMProviderError, TypeError, ValueError, KeyError) as exc:
        logger.warning("Citation page GEO batch failed (%d urls): %s", len(pages), exc)
        return [
            analyze_citation_page_geo(
                page,
                own_brand=own_brand,
                competitors=competitors,
                cache_ttl_s=cache_ttl_s,
            )
            for page in pages
        ]


def analyze_citation_pages_geo(
    pages: list[CitationPageMeta],
    *,
    own_brand: str,
    competitors: list[str],
    cache_ttl_s: int = 0,
    batch_size: int = 8,
) -> list[dict[str, Any]]:
    """Batch-aware Page GEO with per-URL result cache."""
    if not own_brand.strip():
        empty = _empty_page_geo(reason="missing own brand")
        return [empty for _ in pages]

    results: list[dict[str, Any] | None] = [None] * len(pages)
    pending: list[tuple[int, CitationPageMeta]] = []

    for idx, page in enumerate(pages):
        cached = get_page_geo_cached(
            url=page.url,
            text_snippet=page.text_snippet,
            own_brand=own_brand,
            competitors=competitors,
            ttl_s=cache_ttl_s,
        )
        if cached is not None:
            results[idx] = cached
        else:
            pending.append((idx, page))

    if not pending:
        return [r if r is not None else _empty_page_geo(reason="missing") for r in results]

    chunk_size = max(1, batch_size)
    for start in range(0, len(pending), chunk_size):
        chunk = pending[start : start + chunk_size]
        chunk_pages = [page for _, page in chunk]
        chunk_results = _analyze_citation_page_geo_batch(
            chunk_pages,
            own_brand=own_brand,
            competitors=competitors,
            cache_ttl_s=cache_ttl_s,
        )
        for (idx, page), analysis in zip(chunk, chunk_results, strict=True):
            set_page_geo_cached(
                url=page.url,
                text_snippet=page.text_snippet,
                own_brand=own_brand,
                competitors=competitors,
                result=analysis,
                ttl_s=cache_ttl_s,
            )
            results[idx] = analysis

    return [r if r is not None else _empty_page_geo(reason="missing") for r in results]


def heuristic_page_mentioned_brands(
    page: CitationPageMeta,
    *,
    own_brand: str,
    competitors: list[str],
    own_aliases: list[str] | None = None,
) -> list[str]:
    """Fallback: substring match on fetched page text when LLM page GEO is disabled."""
    from aperix_geo.services.sampling.citation_page import page_mentions_any_term

    if not page.fetch_ok or not page.text_snippet:
        return []
    mentioned: list[str] = []
    own_terms = [own_brand, *(own_aliases or [])]
    if page_mentions_any_term(page.text_snippet, own_terms):
        mentioned.append(own_brand)
    for comp in competitors:
        key = comp.strip()
        if key and page_mentions_any_term(page.text_snippet, (key,)) and key not in mentioned:
            mentioned.append(key)
    return mentioned


# 兼容旧 API
def mentioned_brand_names(analysis: dict[str, Any] | None) -> list[str]:
    return page_mentioned_brand_names(analysis)


def normalize_citation_analysis(
    data: dict[str, Any],
    *,
    own_brand: str,
    competitors: list[str],
) -> dict[str, Any]:
    merged = normalize_page_geo(data)
    if isinstance(data.get("brands_sentiment_absa"), dict):
        merged["brands_sentiment_absa"] = normalize_response_absa(
            data, own_brand=own_brand, competitors=competitors
        )["brands_sentiment_absa"]
    return merged


def analyze_citation_source(
    page: CitationPageMeta,
    *,
    own_brand: str,
    competitors: list[str],
) -> dict[str, Any]:
    """Deprecated: use analyze_citation_page_geo."""
    return analyze_citation_page_geo(
        page,
        own_brand=own_brand,
        competitors=competitors,
    )
