"""Document-layer citation payload stored on LLMResponse.parsed."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class CitationDocument:
    citation_urls_own: list[str] = field(default_factory=list)
    citation_sources: list[dict[str, Any]] = field(default_factory=list)


def empty_citation_document() -> CitationDocument:
    return CitationDocument()
