"""Unit tests for Doubao Web HTTP SSE mapping and transport selection."""

from __future__ import annotations

import json

from aperix_geo.config import Settings
from aperix_geo.services.providers.doubao_web.runtime import resolve_crawl_transport
from aperix_geo.services.providers.doubao_web.web_http.map_result import (
    map_sse_events_to_fields,
    map_web_http_to_sampling_result,
)


def test_map_sse_event_2001_text_and_2002_conversation():
    lines = [
        "data: "
        + json.dumps(
            {
                "event_type": 2002,
                "event_data": json.dumps({"conversation_id": "cid-abc"}),
            },
            ensure_ascii=False,
        ),
        "data: "
        + json.dumps(
            {
                "event_type": 2001,
                "event_data": json.dumps(
                    {
                        "message": {
                            "content": json.dumps({"text": "你好"}, ensure_ascii=False),
                        }
                    },
                    ensure_ascii=False,
                ),
            },
            ensure_ascii=False,
        ),
        "data: "
        + json.dumps(
            {
                "event_type": 2001,
                "event_data": json.dumps(
                    {
                        "message": {
                            "content": json.dumps({"text": "世界"}, ensure_ascii=False),
                        }
                    },
                    ensure_ascii=False,
                ),
            },
            ensure_ascii=False,
        ),
    ]
    fields = map_sse_events_to_fields("\n".join(lines))
    assert fields["text"] == "你好世界"
    assert fields["conversation_id"] == "cid-abc"


def test_map_sse_collects_queries_and_urls():
    payload = {
        "event_type": 2001,
        "event_data": json.dumps(
            {
                "message": {
                    "content": json.dumps({"text": "见 https://example.com/a"}, ensure_ascii=False),
                },
                "search_queries": ["露营装备", "帐篷推荐"],
                "references": [{"url": "https://news.example.com/x"}],
            },
            ensure_ascii=False,
        ),
    }
    fields = map_sse_events_to_fields("data: " + json.dumps(payload, ensure_ascii=False))
    assert "露营装备" in fields["search_queries"]
    assert "https://news.example.com/x" in fields["source_urls"]
    assert "https://example.com/a" in fields["source_urls"]


def test_map_web_http_to_sampling_result():
    result = map_web_http_to_sampling_result(
        {
            "text": "hello",
            "search_queries": ["q1"],
            "source_urls": ["https://a.example"],
        },
        latency_ms=12,
        share_url="https://www.doubao.com/share/xxx",
    )
    assert result.text == "hello"
    assert result.search_queries == ("q1",)
    assert result.source_urls == ("https://a.example",)
    assert result.share_url.endswith("xxx")
    assert result.web_search_mode == "doubao_web_crawl"


def test_transport_forced_ui_when_web_http_disabled():
    s = Settings(doubao_web_http_enabled=False, doubao_crawl_transport="hybrid")
    assert resolve_crawl_transport(s) == "ui"


def test_transport_hybrid_when_enabled():
    s = Settings(doubao_web_http_enabled=True, doubao_crawl_transport="hybrid")
    assert resolve_crawl_transport(s) == "hybrid"


def test_transport_ui_default_when_enabled_but_ui():
    s = Settings(doubao_web_http_enabled=True, doubao_crawl_transport="ui")
    assert resolve_crawl_transport(s) == "ui"
