"""Phase 1 — extract: URLs, mention drafts, citation/ABSA inputs."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.orm import Session

from aperix_geo.config import get_settings
from aperix_geo.db.models import Subject
from aperix_geo.services.analysis.entity import own_entity
from aperix_geo.services.brand.keys import configured_brand_keys
from aperix_geo.services.crawl.settings import page_crawl_settings
from aperix_geo.services.sampling.citation import citation_root
from aperix_geo.services.sampling.mentions import (
    CompetitorEntry,
    absa_competitor_keys,
    own_names,
)
from aperix_geo.services.sampling.parse.types import CitationParseParams
from aperix_geo.services.sampling.response_absa import response_absa_needed
from aperix_geo.services.sampling.signal_draft import (
    EntitySignalDraft,
    build_mention_entity_signals,
)
from aperix_geo.utils.url import extract_urls, filter_citation_urls, hostname_from_url


@dataclass(frozen=True)
class ParseContext:
    text: str
    urls: list[str]
    url_hosts: list[str]
    entity_signals: list[EntitySignalDraft]
    own_brand: str
    competitors: list[CompetitorEntry]
    competitor_brand_names: list[str]
    competitor_absa_keys: list[tuple[str, str]]
    configured_brand_keys: frozenset[str]
    citation: CitationParseParams
    absa_needed: bool
    absa_cache_ttl_s: int
    web_search_mode: str
    source_urls: list[str] | None
    subject: Subject
    db: Session | None = None


def extract_citation_urls(raw_text: str, source_urls: list[str] | None) -> tuple[list[str], list[str]]:
    urls = filter_citation_urls(extract_urls(raw_text))
    if source_urls:
        urls = filter_citation_urls(list(dict.fromkeys([*urls, *[url for url in source_urls if url]])))
    url_hosts: list[str] = []
    for url in urls:
        host = hostname_from_url(url)
        if host:
            url_hosts.append(host)
    return urls, url_hosts


def extract_parse_context(
    raw_text: str,
    *,
    subject: Subject,
    source_urls: list[str] | None,
    web_search_mode: str,
    sampling_job_id: UUID | None,
    db: Session | None = None,
) -> ParseContext:
    text = raw_text or ""
    urls, url_hosts = extract_citation_urls(text, source_urls)
    entity_signals, competitors = build_mention_entity_signals(text, subject=subject, url_hosts=url_hosts)
    own = own_entity(subject)
    own_brand = subject.brand or own.label
    own_match_names = own_names(subject)
    competitor_brand_names, competitor_absa_keys = absa_competitor_keys(competitors)
    brand_keys = frozenset(
        configured_brand_keys(
            own_brand=own_brand,
            own_match_names=own_match_names,
            competitor_brand_names=competitor_brand_names,
            competitor_absa_keys=competitor_absa_keys,
        )
    )

    settings = get_settings()
    crawl = page_crawl_settings(settings)
    llm_key = settings.deepseek_api_key.strip()
    absa_needed = response_absa_needed(
        llm_configured=bool(llm_key),
        text=text,
        entity_signals=entity_signals,
    )

    citation_params = CitationParseParams(
        urls=urls,
        root=citation_root(subject),
        own_names=own_names(subject),
        own_brand=own_brand,
        competitors=competitors,
        entity_signals=entity_signals,
        crawl=crawl,
        snippet_chars=settings.citation_text_snippet_chars,
        sampling_job_id=sampling_job_id,
    )

    return ParseContext(
        text=text,
        urls=urls,
        url_hosts=url_hosts,
        entity_signals=entity_signals,
        own_brand=own_brand,
        competitors=competitors,
        competitor_brand_names=competitor_brand_names,
        competitor_absa_keys=competitor_absa_keys,
        configured_brand_keys=brand_keys,
        citation=citation_params,
        absa_needed=absa_needed,
        absa_cache_ttl_s=settings.citation_response_absa_cache_ttl_s,
        web_search_mode=web_search_mode,
        source_urls=source_urls,
        subject=subject,
        db=db,
    )
