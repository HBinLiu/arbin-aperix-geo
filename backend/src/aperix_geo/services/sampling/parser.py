"""Orchestrate LLM response parsing: mentions, citations, ABSA sentiment."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from aperix_geo.config import get_settings
from aperix_geo.db.models import Subject
from aperix_geo.services.crawl.settings import page_crawl_settings
from aperix_geo.services.sampling.citation import (
    analyze_citation_response_absa,
    citation_root,
    empty_citation_result,
    resolve_citation_sources,
)
from aperix_geo.services.sampling.mentions import (
    CompetitorEntry,
    absa_competitor_keys,
    merge_absa_mention_flags,
    parse_mentions_and_rank,
)
from aperix_geo.services.sampling.parsed import ParsedSamplingResult
from aperix_geo.services.sampling.sentiment import parsed_sentiment_from_absa
from aperix_geo.utils.url import extract_urls, filter_citation_urls, hostname_from_url

# Re-export for tests and legacy imports.
from aperix_geo.services.sampling.mentions import (  # noqa: F401
    competitor_entries as _competitor_entries,
    own_names as _own_names,
)


@dataclass(frozen=True)
class _ParseContext:
    text: str
    urls: list[str]
    url_hosts: list[str]
    mention_stats: dict[str, Any]
    own_brand: str
    competitors: list[CompetitorEntry]
    competitor_brand_names: list[str]
    competitor_absa_keys: list[tuple[str, str]]
    citation_kwargs: dict[str, Any]
    absa_needed: bool
    absa_cache_ttl_s: int
    web_search_mode: str
    source_urls: list[str] | None


def _extract_urls(raw_text: str, source_urls: list[str] | None) -> tuple[list[str], list[str]]:
    urls = filter_citation_urls(extract_urls(raw_text))
    if source_urls:
        urls = filter_citation_urls(list(dict.fromkeys([*urls, *[url for url in source_urls if url]])))
    url_hosts: list[str] = []
    for url in urls:
        host = hostname_from_url(url)
        if host:
            url_hosts.append(host)
    return urls, url_hosts


def _build_parse_context(
    raw_text: str,
    *,
    subject: Subject,
    source_urls: list[str] | None,
    web_search_mode: str,
    sampling_job_id: UUID | None,
) -> _ParseContext:
    text = raw_text or ""
    urls, url_hosts = _extract_urls(text, source_urls)
    mention_stats = parse_mentions_and_rank(text, subject=subject, url_hosts=url_hosts)
    competitors = mention_stats["competitors"]
    own_brand = subject.brand or mention_stats["own_label"]
    competitor_brand_names, competitor_absa_keys = absa_competitor_keys(competitors)

    settings = get_settings()
    crawl = page_crawl_settings(settings)
    llm_key = settings.deepseek_api_key.strip()
    absa_needed = bool(text.strip()) and bool(llm_key)

    citation_kwargs = dict(
        urls=urls,
        root=citation_root(subject),
        own_names=mention_stats["own_names"],
        own_brand=own_brand,
        competitors=competitors,
        crawl=crawl,
        snippet_chars=settings.citation_text_snippet_chars,
        llm_enabled=settings.citation_page_geo_llm_enabled and bool(llm_key),
        geo_cache_ttl_s=settings.citation_page_geo_cache_ttl_s,
        geo_batch_size=settings.citation_page_geo_batch_size,
        sampling_job_id=sampling_job_id,
    )

    return _ParseContext(
        text=text,
        urls=urls,
        url_hosts=url_hosts,
        mention_stats=mention_stats,
        own_brand=own_brand,
        competitors=competitors,
        competitor_brand_names=competitor_brand_names,
        competitor_absa_keys=competitor_absa_keys,
        citation_kwargs=citation_kwargs,
        absa_needed=absa_needed,
        absa_cache_ttl_s=settings.citation_response_absa_cache_ttl_s,
        web_search_mode=web_search_mode,
        source_urls=source_urls,
    )


def _run_response_absa(ctx: _ParseContext) -> dict[str, Any]:
    return analyze_citation_response_absa(
        ctx.text,
        own_brand=ctx.own_brand,
        competitors=ctx.competitor_brand_names,
        cache_ttl_s=ctx.absa_cache_ttl_s,
    )


def _run_analysis(ctx: _ParseContext) -> tuple[dict[str, Any], dict[str, Any]]:
    """Run citation resolve and/or response ABSA based on context."""
    need_citation = bool(ctx.urls)
    need_absa = ctx.absa_needed
    citation = empty_citation_result()
    response_absa: dict[str, Any] = {}

    if need_citation and need_absa:
        with ThreadPoolExecutor(max_workers=2) as pool:
            citation_future = pool.submit(resolve_citation_sources, **ctx.citation_kwargs)
            absa_future = pool.submit(_run_response_absa, ctx)
            citation = citation_future.result()
            response_absa = absa_future.result()
    elif need_citation:
        citation = resolve_citation_sources(**ctx.citation_kwargs)
    elif need_absa:
        response_absa = _run_response_absa(ctx)

    return citation, response_absa


def _apply_absa_to_mentions(ctx: _ParseContext, response_absa: dict[str, Any]) -> dict[str, Any]:
    if not response_absa:
        return ctx.mention_stats
    return merge_absa_mention_flags(
        ctx.mention_stats,
        response_absa,
        own_brand=ctx.own_brand,
        competitor_absa_keys=ctx.competitor_absa_keys,
        url_hosts=ctx.url_hosts,
        competitors=ctx.competitors,
    )


def _assemble_parsed(
    ctx: _ParseContext,
    *,
    citation: dict[str, Any],
    response_absa: dict[str, Any],
    mention_stats: dict[str, Any],
) -> ParsedSamplingResult:
    sentiment = {
        "sentiment_own": "neutral",
        "sentiment_score_own": None,
        "sentiment_reason_own": None,
        "sentiment_competitors": {},
        "sentiment_scores_competitors": {},
        "sentiment_reasons_competitors": {},
        "sentiment_source": "none",
    }
    if response_absa:
        sentiment = parsed_sentiment_from_absa(
            response_absa,
            own_brand=ctx.own_brand,
            competitor_keys=ctx.competitor_absa_keys,
        )

    return ParsedSamplingResult(
        urls=ctx.urls,
        url_hosts=ctx.url_hosts,
        mentions_own=bool(mention_stats["mentions_own"]),
        mention_count_own=int(mention_stats["mention_count_own"]),
        mentions_competitors=dict(mention_stats["mentions_competitors"]),
        mention_counts_competitors=dict(mention_stats["mention_counts_competitors"]),
        sentiment_own=sentiment["sentiment_own"],
        sentiment_score_own=sentiment["sentiment_score_own"],
        sentiment_reason_own=sentiment["sentiment_reason_own"],
        sentiment_competitors=sentiment["sentiment_competitors"],
        sentiment_scores_competitors=sentiment["sentiment_scores_competitors"],
        sentiment_reasons_competitors=sentiment["sentiment_reasons_competitors"],
        sentiment_source=sentiment["sentiment_source"],
        web_search_mode=ctx.web_search_mode,
        source_urls_from_api=list(ctx.source_urls or []),
        rank_hints_first_index=dict(mention_stats["rank_hints_first_index"]),
        rank_own=mention_stats["rank_own"],
        own_brand=ctx.own_brand,
        citation_response_absa=response_absa,
        citation_urls_own=list(citation.get("citation_urls_own") or []),
        has_own_domain_link=bool(citation.get("has_own_domain_link")),
        cited_own_domain=bool(citation.get("cited_own_domain")),
        citation_sources=list(citation.get("citation_sources") or []),
        has_competitor_domain_links=dict(citation.get("has_competitor_domain_links") or {}),
        cited_competitors_on_source=dict(citation.get("cited_competitors_on_source") or {}),
    )


def parse_llm_output_typed(
    raw_text: str,
    *,
    subject: Subject,
    source_urls: list[str] | None = None,
    web_search_mode: str = "none",
    sampling_job_id: UUID | None = None,
) -> ParsedSamplingResult:
    ctx = _build_parse_context(
        raw_text,
        subject=subject,
        source_urls=source_urls,
        web_search_mode=web_search_mode,
        sampling_job_id=sampling_job_id,
    )
    citation, response_absa = _run_analysis(ctx)
    mention_stats = _apply_absa_to_mentions(ctx, response_absa)
    return _assemble_parsed(ctx, citation=citation, response_absa=response_absa, mention_stats=mention_stats)


def parse_llm_output(
    raw_text: str,
    *,
    subject: Subject,
    source_urls: list[str] | None = None,
    web_search_mode: str = "none",
    sampling_job_id: UUID | None = None,
) -> dict[str, Any]:
    return parse_llm_output_typed(
        raw_text,
        subject=subject,
        source_urls=source_urls,
        web_search_mode=web_search_mode,
        sampling_job_id=sampling_job_id,
    ).to_dict()
