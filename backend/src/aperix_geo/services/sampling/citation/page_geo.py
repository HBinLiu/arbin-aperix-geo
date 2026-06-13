"""Per-URL page GEO classification and source-page brand mentions."""

from __future__ import annotations

import logging
from typing import Any

from aperix_geo.services.providers import LLMProviderError, chat_completion
from aperix_geo.services.providers.prompts import (
    CITATION_PAGE_GEO_SYSTEM,
    citation_page_geo_user_content,
)
from aperix_geo.services.sampling.citation.cache.page_geo import (
    get_page_geo_cached,
    page_geo_cache_digest,
    set_page_geo_cached,
)
from aperix_geo.services.sampling.citation.page import CitationPageMeta, page_mentions_any_term
from aperix_geo.utils.cache import run_single_flight
from aperix_geo.utils.json import extract_json_object

logger = logging.getLogger(__name__)


def normalize_page_geo(data: dict[str, Any]) -> dict[str, Any]:
    domain_cls = data.get("domain_classification") if isinstance(data.get("domain_classification"), dict) else {}
    url_cls = data.get("url_classification") if isinstance(data.get("url_classification"), dict) else {}
    page_brands_raw = data.get("page_mentioned_brands")
    page_mentioned_brands: list[str] = []
    if isinstance(page_brands_raw, list):
        page_mentioned_brands = [str(name).strip() for name in page_brands_raw if str(name).strip()]
    return {
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


def _empty_page_geo(*, reason: str) -> dict[str, Any]:
    return {
        "domain_classification": {"type": "", "reason": reason},
        "url_classification": {"type": "", "reason": reason},
        "page_mentioned_brands": [],
        "analysis_source": "failed",
        "failure_reason": reason,
    }


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
        try:
            results = _call_citation_page_geo_llm(
                [page],
                own_brand=own_brand,
                competitors=competitors,
            )
            result = results[0]
        except (LLMProviderError, TypeError, ValueError, KeyError) as exc:
            logger.warning("Citation page GEO failed for %s: %s", page.url, exc)
            return _empty_page_geo(reason=str(exc)[:500])
        set_page_geo_cached(
            url=page.url,
            text_snippet=page.text_snippet,
            own_brand=own_brand,
            competitors=competitors,
            result=result,
            ttl_s=cache_ttl_s,
        )
        return result

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


def _page_geo_entry(page: CitationPageMeta) -> dict[str, object]:
    status_text = str(page.http_status) if (page.http_status or 0) > 0 else "（未知）"
    return {
        "url": page.url,
        "domain": page.domain,
        "http_status": status_text,
        "title": page.title or "（无）",
        "description": page.description or "（无）",
        "headings_list": page.headings_list,
        "has_table": page.has_table,
        "has_code_block": page.has_code_block,
        "text_snippet": page.text_snippet or "（无）",
    }


def _page_geo_batch_entries(pages: list[CitationPageMeta]) -> list[dict[str, object]]:
    return [_page_geo_entry(page) for page in pages]


def _call_citation_page_geo_llm(
    pages: list[CitationPageMeta],
    *,
    own_brand: str,
    competitors: list[str],
) -> list[dict[str, Any]]:
    if not pages:
        return []

    messages = [
        {"role": "system", "content": CITATION_PAGE_GEO_SYSTEM},
        {
            "role": "user",
            "content": citation_page_geo_user_content(
                own_brand=own_brand,
                competitors=competitors,
                pages=_page_geo_batch_entries(pages),
            ),
        },
    ]
    text, _, _ = chat_completion(messages, temperature=0.0, json_mode=True)
    data = extract_json_object(text)
    if not isinstance(data, dict):
        raise ValueError("page geo is not an object")
    rows = data.get("pages")
    if not isinstance(rows, list):
        raise ValueError("page geo missing pages array")

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
            raise ValueError(f"page geo missing url {page.url}")
        out.append(hit)
    return out


def _analyze_citation_page_geo_batch(
    pages: list[CitationPageMeta],
    *,
    own_brand: str,
    competitors: list[str],
    cache_ttl_s: int = 0,
) -> list[dict[str, Any]]:
    if not pages:
        return []
    try:
        return _call_citation_page_geo_llm(
            pages,
            own_brand=own_brand,
            competitors=competitors,
        )
    except (LLMProviderError, TypeError, ValueError, KeyError) as exc:
        logger.warning("Citation page GEO batch failed (%d urls): %s", len(pages), exc)
        if len(pages) == 1:
            return [_empty_page_geo(reason=str(exc)[:500])]
        out: list[dict[str, Any]] = []
        for page in pages:
            try:
                out.extend(
                    _call_citation_page_geo_llm(
                        [page],
                        own_brand=own_brand,
                        competitors=competitors,
                    )
                )
            except (LLMProviderError, TypeError, ValueError, KeyError) as single_exc:
                logger.warning("Citation page GEO failed for %s: %s", page.url, single_exc)
                out.append(_empty_page_geo(reason=str(single_exc)[:500]))
        return out


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
