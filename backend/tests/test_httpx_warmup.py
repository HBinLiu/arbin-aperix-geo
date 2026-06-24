"""Tests for httpx client warmup and citation snippet truncation."""

from unittest.mock import patch

from aperix_geo.services.crawl._httpx import get_httpx_client, warmup_http_stack
from aperix_geo.services.crawl.types import PageFetchResult
from aperix_geo.services.sampling.citation.page import _citation_meta_from_fetch


def test_warmup_http_stack_initializes_clients() -> None:
    with patch("aperix_geo.services.crawl._httpx.httpx.Client") as mock_client_cls:
        warmup_http_stack()
    assert mock_client_cls.call_count == 2


def test_warmup_http_stack_reuses_thread_local_clients() -> None:
    warmup_http_stack()
    first = get_httpx_client()
    second = get_httpx_client()
    assert first is second


def test_citation_meta_from_fetch_truncates_snippet() -> None:
    html = "<html><head><title>T</title></head><body><p>" + ("word " * 500) + "</p></body></html>"
    fetched = PageFetchResult(
        url="https://example.com/a",
        final_url="https://example.com/a",
        http_status=200,
        html=html,
        source="httpx",
    )
    meta = _citation_meta_from_fetch(
        "https://example.com/a",
        domain="example.com",
        fetched=fetched,
        snippet_chars=80,
        html_limit=8000,
    )
    assert meta.fetch_ok
    assert len(meta.text_snippet) <= 80 + 20
