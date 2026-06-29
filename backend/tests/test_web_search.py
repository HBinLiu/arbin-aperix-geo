"""Tests for SearXNG search client."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from aperix_geo.services.searxng import (
    SearchHit,
    _is_usable_result_url,
    _search_searxng,
    search_text,
)
from aperix_geo.utils.url import host_from_url


def test_host_from_url_strips_www() -> None:
    assert host_from_url("https://www.Stripe.com/pricing") == "stripe.com"


def test_host_from_url_invalid() -> None:
    assert host_from_url("") is None
    assert host_from_url("not-a-url") is None


def test_is_usable_result_url_rejects_baidu() -> None:
    assert not _is_usable_result_url("http://www.baidu.com/link?url=abc")
    assert not _is_usable_result_url("https://www.baidu.com/")
    assert _is_usable_result_url("https://www.airwallex.com/cn")


def test_search_searxng_parses_json() -> None:
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {
        "results": [
            {
                "title": "Wise 官网",
                "url": "https://wise.com/business",
                "content": "跨境汇款",
            },
            {"title": "百度", "url": "https://www.baidu.com/", "content": "skip"},
        ],
    }
    with patch("aperix_geo.services.searxng.httpx.get", return_value=mock_resp) as mock_get:
        hits = _search_searxng("跨境支付 竞品", max_results=10, base_url="http://127.0.0.1:8061")

    assert len(hits) == 1
    assert hits[0].url == "https://wise.com/business"
    mock_get.assert_called_once()
    call_kwargs = mock_get.call_args.kwargs
    assert call_kwargs["params"]["format"] == "json"
    assert call_kwargs["params"]["q"] == "跨境支付 竞品"
    assert "engines" not in call_kwargs["params"]


@patch("aperix_geo.services.searxng._search_searxng")
@patch("aperix_geo.services.searxng.get_settings")
def test_search_text_delegates_to_searxng(mock_settings, mock_searx) -> None:
    mock_settings.return_value.searxng_base_url = "http://127.0.0.1:8061"
    mock_settings.return_value.searxng_timeout_s = 30.0
    mock_searx.return_value = [SearchHit(title="A", url="https://a.com", snippet="", query="q")]
    hits = search_text("q")
    assert len(hits) == 1
    mock_searx.assert_called_once_with(
        "q",
        max_results=10,
        base_url="http://127.0.0.1:8061",
        timeout_s=30.0,
    )


@patch("aperix_geo.services.searxng.get_settings")
def test_search_text_empty_without_base_url(mock_settings) -> None:
    mock_settings.return_value.searxng_base_url = ""
    assert search_text("q") == []
