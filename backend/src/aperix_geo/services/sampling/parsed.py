"""Typed parse result for one LLM sampling response."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class ParsedSamplingResult:
    urls: list[str] = field(default_factory=list)
    url_hosts: list[str] = field(default_factory=list)
    mentions_own: bool = False
    mention_count_own: int = 0
    mentions_competitors: dict[str, bool] = field(default_factory=dict)
    mention_counts_competitors: dict[str, int] = field(default_factory=dict)
    sentiment_own: str = "neutral"
    sentiment_score_own: float | None = None
    sentiment_reason_own: str | None = None
    sentiment_competitors: dict[str, str] = field(default_factory=dict)
    sentiment_scores_competitors: dict[str, float] = field(default_factory=dict)
    sentiment_reasons_competitors: dict[str, str] = field(default_factory=dict)
    sentiment_source: str = "none"
    web_search_mode: str = "none"
    source_urls_from_api: list[str] = field(default_factory=list)
    rank_hints_first_index: dict[str, int | None] = field(default_factory=dict)
    rank_own: int | None = None
    own_brand: str = ""
    citation_response_absa: dict[str, Any] = field(default_factory=dict)
    citation_urls_own: list[str] = field(default_factory=list)
    has_own_domain_link: bool = False
    cited_own_domain: bool = False
    citation_sources: list[dict[str, Any]] = field(default_factory=list)
    has_competitor_domain_links: dict[str, bool] = field(default_factory=dict)
    cited_competitors_on_source: dict[str, bool] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ParsedSamplingResult:
        return cls(
            urls=list(data.get("urls") or []),
            url_hosts=list(data.get("url_hosts") or []),
            mentions_own=bool(data.get("mentions_own")),
            mention_count_own=int(data.get("mention_count_own") or 0),
            mentions_competitors=dict(data.get("mentions_competitors") or {}),
            mention_counts_competitors={
                str(key): int(value or 0)
                for key, value in (data.get("mention_counts_competitors") or {}).items()
            },
            sentiment_own=str(data.get("sentiment_own") or "neutral"),
            sentiment_score_own=data.get("sentiment_score_own"),
            sentiment_reason_own=data.get("sentiment_reason_own"),
            sentiment_competitors=dict(data.get("sentiment_competitors") or {}),
            sentiment_scores_competitors={
                str(key): float(value)
                for key, value in (data.get("sentiment_scores_competitors") or {}).items()
            },
            sentiment_reasons_competitors=dict(data.get("sentiment_reasons_competitors") or {}),
            sentiment_source=str(data.get("sentiment_source") or "none"),
            web_search_mode=str(data.get("web_search_mode") or "none"),
            source_urls_from_api=list(data.get("source_urls_from_api") or []),
            rank_hints_first_index=dict(data.get("rank_hints_first_index") or {}),
            rank_own=data.get("rank_own"),
            own_brand=str(data.get("own_brand") or ""),
            citation_response_absa=dict(data.get("citation_response_absa") or {}),
            citation_urls_own=list(data.get("citation_urls_own") or []),
            has_own_domain_link=bool(data.get("has_own_domain_link")),
            cited_own_domain=bool(data.get("cited_own_domain")),
            citation_sources=list(data.get("citation_sources") or []),
            has_competitor_domain_links=dict(data.get("has_competitor_domain_links") or {}),
            cited_competitors_on_source=dict(data.get("cited_competitors_on_source") or {}),
        )
