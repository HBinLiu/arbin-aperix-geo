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
from aperix_geo.services.sampling.citation.geo_classify import (
    GeoClassification,
    classify_citation_page_geo,
    geo_classification_to_analysis,
    merge_geo_analysis,
)
from aperix_geo.services.sampling.citation.page import CitationPageMeta, page_mentions_any_term
from aperix_geo.utils.cache import run_single_flight
from aperix_geo.utils.json import extract_json_object

logger = logging.getLogger(__name__)


def normalize_page_geo(data: dict[str, Any]) -> dict[str, Any]:
    """Parse LLM page GEO output (classifications only; brand mentions are computed in code)."""
    domain_cls = data.get("domain_classification") if isinstance(data.get("domain_classification"), dict) else {}
    url_cls = data.get("url_classification") if isinstance(data.get("url_classification"), dict) else {}
    return {
        "domain_classification": {
            "type": str(domain_cls.get("type") or domain_cls.get("detected_domain_type") or "").strip(),
            "reason": str(domain_cls.get("reason") or domain_cls.get("domain_reason") or "").strip(),
        },
        "url_classification": {
            "type": str(url_cls.get("type") or url_cls.get("detected_type") or "").strip(),
            "reason": str(url_cls.get("reason") or url_cls.get("classification_reason") or "").strip(),
        },
        "page_mentioned_brands": [],
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


def page_mentioned_brands_from_snippet(
    page: CitationPageMeta,
    *,
    page_brand_scope: list[str],
    match_terms_by_brand: dict[str, list[str]],
) -> list[str]:
    """Match page_brand_scope against text_snippet (case-insensitive substring + alias terms)."""
    if not page_brand_scope:
        return []
    if page.http_status is not None and page.http_status != 200:
        return []
    if not page.fetch_ok or not (page.text_snippet or "").strip():
        return []
    mentioned: list[str] = []
    for brand in page_brand_scope:
        terms = match_terms_by_brand.get(brand, [brand])
        if page_mentions_any_term(page.text_snippet, terms) and brand not in mentioned:
            mentioned.append(brand)
    return mentioned


def attach_page_mentioned_brands(
    page: CitationPageMeta,
    analysis: dict[str, Any],
    *,
    page_brand_scope: list[str],
    match_terms_by_brand: dict[str, list[str]],
) -> dict[str, Any]:
    out = dict(analysis)
    out["page_mentioned_brands"] = page_mentioned_brands_from_snippet(
        page,
        page_brand_scope=page_brand_scope,
        match_terms_by_brand=match_terms_by_brand,
    )
    return out


def _rule_classifications(
    pages: list[CitationPageMeta],
    *,
    enterprise_roots: frozenset[str] | set[str],
    page_brand_scope: list[str],
) -> list[GeoClassification]:
    return [
        classify_citation_page_geo(
            page,
            enterprise_roots=enterprise_roots,
            page_brand_scope=page_brand_scope,
        )
        for page in pages
    ]


def _analysis_from_rule(
    page: CitationPageMeta,
    rule: GeoClassification,
    *,
    page_brand_scope: list[str],
    match_terms_by_brand: dict[str, list[str]],
) -> dict[str, Any]:
    return attach_page_mentioned_brands(
        page,
        geo_classification_to_analysis(rule, analysis_source="rule"),
        page_brand_scope=page_brand_scope,
        match_terms_by_brand=match_terms_by_brand,
    )


def _analysis_from_merge(
    page: CitationPageMeta,
    rule: GeoClassification,
    llm: dict[str, Any],
    *,
    page_brand_scope: list[str],
    match_terms_by_brand: dict[str, list[str]],
) -> dict[str, Any]:
    merged = merge_geo_analysis(rule, llm)
    return attach_page_mentioned_brands(
        page,
        merged,
        page_brand_scope=page_brand_scope,
        match_terms_by_brand=match_terms_by_brand,
    )


def analyze_citation_page_geo(
    page: CitationPageMeta,
    *,
    own_brand: str,
    page_brand_scope: list[str],
    match_terms_by_brand: dict[str, list[str]],
    enterprise_roots: frozenset[str] | set[str] | None = None,
    cache_ttl_s: int = 0,
    llm_enabled: bool = True,
) -> dict[str, Any]:
    """Schema + rules first; optional LLM fallback for unresolved fields."""
    if not own_brand.strip():
        return _empty_page_geo(reason="missing own brand")

    roots = enterprise_roots or frozenset()
    rule = classify_citation_page_geo(
        page,
        enterprise_roots=roots,
        page_brand_scope=page_brand_scope,
    )

    if rule.complete or not llm_enabled:
        return _analysis_from_rule(
            page,
            rule,
            page_brand_scope=page_brand_scope,
            match_terms_by_brand=match_terms_by_brand,
        )

    def _read_cache() -> dict[str, Any] | None:
        raw = get_page_geo_cached(
            url=page.url,
            text_snippet=page.text_snippet,
            ttl_s=cache_ttl_s,
        )
        if raw is None:
            return None
        return _analysis_from_merge(
            page,
            rule,
            raw,
            page_brand_scope=page_brand_scope,
            match_terms_by_brand=match_terms_by_brand,
        )

    cached = _read_cache()
    if cached is not None:
        return cached

    def _fetch() -> dict[str, Any]:
        try:
            results = _call_citation_page_geo_llm([page])
            llm_result = results[0]
        except (LLMProviderError, TypeError, ValueError, KeyError) as exc:
            logger.warning("Citation page GEO failed for %s: %s", page.url, exc)
            return _analysis_from_merge(
                page,
                rule,
                {},
                page_brand_scope=page_brand_scope,
                match_terms_by_brand=match_terms_by_brand,
            )
        if llm_result.get("analysis_source") != "failed":
            set_page_geo_cached(
                url=page.url,
                text_snippet=page.text_snippet,
                result=llm_result,
                ttl_s=cache_ttl_s,
            )
        return _analysis_from_merge(
            page,
            rule,
            llm_result,
            page_brand_scope=page_brand_scope,
            match_terms_by_brand=match_terms_by_brand,
        )

    if cache_ttl_s <= 0:
        return _fetch()

    digest = page_geo_cache_digest(
        url=page.url,
        text_snippet=page.text_snippet,
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
        "schema_types": list(page.schema_types),
        "content_type": page.content_type or "（无）",
    }


def _page_geo_batch_entries(pages: list[CitationPageMeta]) -> list[dict[str, object]]:
    return [_page_geo_entry(page) for page in pages]


def _call_citation_page_geo_llm(pages: list[CitationPageMeta]) -> list[dict[str, Any]]:
    if not pages:
        return []

    messages = [
        {"role": "system", "content": CITATION_PAGE_GEO_SYSTEM},
        {
            "role": "user",
            "content": citation_page_geo_user_content(
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


def _analyze_citation_page_geo_batch(pages: list[CitationPageMeta]) -> list[dict[str, Any]]:
    if not pages:
        return []
    try:
        return _call_citation_page_geo_llm(pages)
    except (LLMProviderError, TypeError, ValueError, KeyError) as exc:
        logger.warning("Citation page GEO batch failed (%d urls): %s", len(pages), exc)
        if len(pages) == 1:
            return [_empty_page_geo(reason=str(exc)[:500])]
        out: list[dict[str, Any]] = []
        for page in pages:
            try:
                out.extend(_call_citation_page_geo_llm([page]))
            except (LLMProviderError, TypeError, ValueError, KeyError) as single_exc:
                logger.warning("Citation page GEO failed for %s: %s", page.url, single_exc)
                out.append(_empty_page_geo(reason=str(single_exc)[:500]))
        return out


def analyze_citation_pages_geo(
    pages: list[CitationPageMeta],
    *,
    own_brand: str,
    page_brand_scope: list[str],
    match_terms_by_brand: dict[str, list[str]],
    enterprise_roots: frozenset[str] | set[str] | None = None,
    cache_ttl_s: int = 0,
    batch_size: int = 8,
    llm_enabled: bool = True,
) -> list[dict[str, Any]]:
    """Schema + rules first; LLM fallback for unresolved fields; brand mentions from snippet."""
    if not own_brand.strip():
        empty = _empty_page_geo(reason="missing own brand")
        return [empty for _ in pages]

    roots = enterprise_roots or frozenset()
    rules = _rule_classifications(
        pages,
        enterprise_roots=roots,
        page_brand_scope=page_brand_scope,
    )

    if not llm_enabled:
        return [
            _analysis_from_rule(
                page,
                rule,
                page_brand_scope=page_brand_scope,
                match_terms_by_brand=match_terms_by_brand,
            )
            for page, rule in zip(pages, rules, strict=True)
        ]

    results: list[dict[str, Any] | None] = [None] * len(pages)
    pending: list[tuple[int, CitationPageMeta, GeoClassification]] = []

    for idx, (page, rule) in enumerate(zip(pages, rules, strict=True)):
        if rule.complete:
            results[idx] = _analysis_from_rule(
                page,
                rule,
                page_brand_scope=page_brand_scope,
                match_terms_by_brand=match_terms_by_brand,
            )
            continue

        cached_llm = get_page_geo_cached(
            url=page.url,
            text_snippet=page.text_snippet,
            ttl_s=cache_ttl_s,
        )
        if cached_llm is not None:
            results[idx] = _analysis_from_merge(
                page,
                rule,
                cached_llm,
                page_brand_scope=page_brand_scope,
                match_terms_by_brand=match_terms_by_brand,
            )
        else:
            pending.append((idx, page, rule))

    if not pending:
        return [r if r is not None else _empty_page_geo(reason="missing") for r in results]

    chunk_size = max(1, batch_size)
    for start in range(0, len(pending), chunk_size):
        chunk = pending[start : start + chunk_size]
        chunk_pages = [page for _, page, _ in chunk]
        chunk_results = _analyze_citation_page_geo_batch(chunk_pages)
        for (idx, page, rule), llm_analysis in zip(chunk, chunk_results, strict=True):
            if llm_analysis.get("analysis_source") != "failed":
                set_page_geo_cached(
                    url=page.url,
                    text_snippet=page.text_snippet,
                    result=llm_analysis,
                    ttl_s=cache_ttl_s,
                )
            results[idx] = _analysis_from_merge(
                page,
                rule,
                llm_analysis if llm_analysis.get("analysis_source") != "failed" else {},
                page_brand_scope=page_brand_scope,
                match_terms_by_brand=match_terms_by_brand,
            )

    return [r if r is not None else _empty_page_geo(reason="missing") for r in results]


# Backward-compatible alias
heuristic_page_mentioned_brands = page_mentioned_brands_from_snippet
