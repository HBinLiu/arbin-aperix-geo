"""Page fetch result types."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from aperix_geo.utils.html import html_to_text
from aperix_geo.services.crawl.seo import parse_seo_from_html, seo_has_signal

FetchSource = Literal["httpx", "crawl4ai", "none"]
_FETCH_OK_PARSE_LIMIT = 120_000


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
        seo = (
            parse_seo_from_html(self.html[:_FETCH_OK_PARSE_LIMIT], include_microdata=False)
            if self.html
            else None
        )
        if seo and seo_has_signal(seo):
            return True
        if self.markdown.strip():
            return len(self.markdown.strip()) >= 40
        if self.html:
            body = html_to_text(self.html, limit=2000)
            return len(body.strip()) >= 40
        return False
