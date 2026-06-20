"""Shared parse pipeline types."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from aperix_geo.services.crawl.settings import PageCrawlSettings
from aperix_geo.services.sampling.citation import CitationDocument
from aperix_geo.services.sampling.mentions import CompetitorEntry
from aperix_geo.services.sampling.signal_draft import EntitySignalDraft


@dataclass(frozen=True)
class CitationParseParams:
    """Typed citation/GEO inputs (replaces citation_kwargs dict)."""

    urls: list[str]
    root: str | None
    own_names: list[str]
    own_brand: str
    competitors: list[CompetitorEntry]
    entity_signals: list[EntitySignalDraft]
    crawl: PageCrawlSettings
    snippet_chars: int
    llm_enabled: bool
    geo_cache_ttl_s: int
    geo_batch_size: int
    sampling_job_id: UUID | None = None


@dataclass(frozen=True)
class ParseEnrichment:
    """Phase 2 output: ABSA + citation document."""

    citation: CitationDocument
    response_absa: dict[str, Any]


@dataclass(frozen=True)
class ParseMergeResult:
    """Phase 3 output: entity drafts ready for persist."""

    entity_signals: list[EntitySignalDraft]
    sentiment_source: str
    response_absa: dict[str, Any]
