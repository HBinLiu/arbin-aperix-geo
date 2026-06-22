"""Tests for favicon caching during citation page fetch."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from aperix_geo.services.favicon._citation import (
    favicon_cached_for_domain,
    maybe_cache_favicon_from_page_html,
)


def test_maybe_cache_favicon_skips_when_domain_already_cached(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("FAVICON_STORAGE_DIR", str(tmp_path))
    from aperix_geo.services.favicon._storage import persist_favicon

    persist_favicon(
        "cached.wise.com",
        url="https://cached.wise.com/favicon.ico",
        body=b"icon",
        media_type="image/x-icon",
    )
    assert favicon_cached_for_domain("cached.wise.com") is True

    with patch("aperix_geo.services.favicon._citation.fetch_first_icon") as mock_fetch:
        assert (
            maybe_cache_favicon_from_page_html(
                page_url="https://cached.wise.com/article",
                html='<html><link rel="icon" href="/favicon.ico"></html>',
            )
            is False
        )
        mock_fetch.assert_not_called()


@patch("aperix_geo.services.favicon._citation.fetch_first_icon")
def test_maybe_cache_favicon_from_page_html(mock_fetch: MagicMock, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("FAVICON_STORAGE_DIR", str(tmp_path))
    mock_fetch.return_value = (b"png-bytes", "image/png")

    html = """
    <html><head>
      <link rel="icon" href="https://news.wise.com/static/favicon.png">
    </head></html>
    """
    assert maybe_cache_favicon_from_page_html(
        page_url="https://news.wise.com/articles/1",
        html=html,
    ) is True

    mock_fetch.assert_called_once()
    domain, candidates = mock_fetch.call_args[0][1], mock_fetch.call_args[0][2]
    assert domain == "news.wise.com"
    assert candidates


@patch("aperix_geo.services.favicon._citation.fetch_first_icon")
def test_fetch_citation_page_meta_caches_favicon(mock_fetch: MagicMock, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("FAVICON_STORAGE_DIR", str(tmp_path))
    mock_fetch.return_value = (b"ico", "image/x-icon")

    from aperix_geo.services.sampling.citation.page import fetch_citation_page_meta

    fetched = MagicMock()
    fetched.http_status = 200
    fetched.source = "httpx"
    fetched.fetch_ok = True
    fetched.final_url = "https://blog.wise.com/post"
    fetched.html = '<html><head><link rel="icon" href="/favicon.ico"></head><body><p>x</p></body></html>'
    fetched.markdown = ""

    settings = MagicMock()
    settings.citation_favicon_inline = True

    with (
        patch("aperix_geo.services.sampling.citation.page.fetch_page", return_value=fetched),
        patch("aperix_geo.services.favicon._citation.get_settings", return_value=settings),
    ):
        meta = fetch_citation_page_meta("https://blog.wise.com/post")

    assert meta.fetch_ok is True
    mock_fetch.assert_called_once()
