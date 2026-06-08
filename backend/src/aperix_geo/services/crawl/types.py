"""Page fetch result types."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from aperix_geo.utils.html import html_to_text, parse_head_from_html

FetchSource = Literal["httpx", "crawl4ai", "none"]


@dataclass(frozen=True)
class PageFetchResult:
    url: str
    final_url: str = ""
    http_status: int | None = None
    html: str = ""
    markdown: str = ""
    source: FetchSource = "none"

    @property
    def fetch_ok(self) -> bool:
        if self.source == "none":
            return False
        title, description = parse_head_from_html(self.html[:120_000]) if self.html else ("", "")
        if title or description:
            return True
        if self.markdown.strip():
            return len(self.markdown.strip()) >= 40
        if self.html:
            body = html_to_text(self.html, limit=2000)
            return len(body.strip()) >= 40
        return False
