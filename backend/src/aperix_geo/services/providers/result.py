"""Shared chat completion result returned by sampling providers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class SamplingChatResult:
    text: str
    usage: dict[str, Any]
    latency_ms: int
    source_urls: tuple[str, ...] = ()
    web_search_mode: str = "none"
    # Engine web-search queries extracted from tool traces (query fan-out).
    search_queries: tuple[str, ...] = ()
    # Doubao web-crawl share link; API paths leave empty (column on tb_llm_responses).
    share_url: str = ""
