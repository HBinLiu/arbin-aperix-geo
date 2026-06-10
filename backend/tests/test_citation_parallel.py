"""Tests for parallel citation page fetch."""

from __future__ import annotations

import threading
from unittest.mock import patch

from aperix_geo.services.sampling.citation import (
    CitationPageMeta,
    fetch_citation_pages_parallel,
)


def test_fetch_citation_pages_parallel_preserves_order() -> None:
    urls = ["https://a.test/1", "https://b.test/2", "https://c.test/3"]
    active = {"n": 0}
    lock = threading.Lock()

    def _fetch(url: str, **kwargs) -> CitationPageMeta:
        with lock:
            active["n"] += 1
            assert active["n"] <= 2
        try:
            host = url.split("/")[2]
            return CitationPageMeta(url=url, domain=host, fetch_ok=True, title=host)
        finally:
            with lock:
                active["n"] -= 1

    with patch(
        "aperix_geo.services.sampling.citation.page.fetch_citation_page_meta",
        side_effect=_fetch,
    ):
        pages = fetch_citation_pages_parallel(urls, concurrency=2)

    assert [p.url for p in pages] == urls
    assert [p.title for p in pages] == ["a.test", "b.test", "c.test"]

