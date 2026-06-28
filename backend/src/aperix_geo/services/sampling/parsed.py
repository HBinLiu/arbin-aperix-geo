"""Typed parse result for one LLM sampling response."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from aperix_geo.services.sampling.signal_draft import EntitySignalDraft


@dataclass
class ParsedSamplingResult:
    urls: list[str] = field(default_factory=list)
    url_hosts: list[str] = field(default_factory=list)
    web_search_mode: str = "none"
    source_urls_from_api: list[str] = field(default_factory=list)
    own_brand: str = ""
    sentiment_source: str = "none"
    citation_response_absa: dict[str, Any] = field(default_factory=dict)
    citation_urls_own: list[str] = field(default_factory=list)
    citation_sources: list[dict[str, Any]] = field(default_factory=list)
    entity_signals: list[EntitySignalDraft] = field(default_factory=list)
    absa_live_call: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Document-layer fields for JSONB storage (entity KPIs live in tb_llm_response_signals)."""
        data = asdict(self)
        data.pop("entity_signals", None)
        data.pop("absa_live_call", None)
        return data

    def to_api_dict(self, *, entity_signal_records: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        """Storage dict plus entity_signals for API responses."""
        data = self.to_dict()
        if entity_signal_records is not None:
            data["entity_signals"] = entity_signal_records
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ParsedSamplingResult:
        from aperix_geo.services.sampling.signal_draft import drafts_from_records

        return cls(
            urls=list(data.get("urls") or []),
            url_hosts=list(data.get("url_hosts") or []),
            web_search_mode=str(data.get("web_search_mode") or "none"),
            source_urls_from_api=list(data.get("source_urls_from_api") or []),
            own_brand=str(data.get("own_brand") or ""),
            sentiment_source=str(data.get("sentiment_source") or "none"),
            citation_response_absa=dict(data.get("citation_response_absa") or {}),
            citation_urls_own=list(data.get("citation_urls_own") or []),
            citation_sources=list(data.get("citation_sources") or []),
            entity_signals=drafts_from_records(list(data.get("entity_signals") or [])),
        )
