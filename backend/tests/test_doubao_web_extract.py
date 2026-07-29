"""Unit tests for Doubao Web panel extraction (no live browser)."""

from __future__ import annotations

from pathlib import Path

import pytest

from aperix_geo.config import Settings
from aperix_geo.services.providers.doubao_web.accounts import load_storage_state, resolve_storage_state_path
from aperix_geo.services.providers.doubao_web.crawler import user_prompt_from_messages
from aperix_geo.services.providers.doubao_web.errors import DoubaoLoginExpired
from aperix_geo.services.providers.doubao_web.extract import (
    extract_quoted_queries,
    extract_urls,
    panel_counts,
    panel_present,
    pick_share_url,
)


SAMPLE_PANEL = """
搜索 3 个关键词，参考 5 篇资料
“适合小团队的CRM”
「国产 CRM 推荐」
"hubspot alternative china"
1. https://example.com/a
2. https://example.com/b
"""


def test_panel_present_and_counts() -> None:
    assert panel_present(SAMPLE_PANEL)
    assert panel_counts(SAMPLE_PANEL) == (3, 5)
    assert not panel_present("普通回复没有联网面板")


def test_extract_quoted_queries() -> None:
    queries = extract_quoted_queries(SAMPLE_PANEL)
    assert queries == (
        "适合小团队的CRM",
        "国产 CRM 推荐",
        "hubspot alternative china",
    )


def test_extract_urls_and_pick_share() -> None:
    urls = extract_urls(SAMPLE_PANEL)
    assert urls[0] == "https://example.com/a"
    assert pick_share_url(
        ["https://example.com/x", "https://www.doubao.com/share/abc123"]
    ).startswith("https://www.doubao.com/share/")


def test_user_prompt_from_messages() -> None:
    assert user_prompt_from_messages(
        [{"role": "system", "content": "s"}, {"role": "user", "content": " hello "}]
    ) == "hello"


def test_resolve_storage_state_missing() -> None:
    s = Settings(doubao_crawl_storage_state_path="/tmp/does-not-exist-doubao.json")
    assert resolve_storage_state_path(s) is None


def test_load_storage_state_requires_cookies(tmp_path: Path) -> None:
    path = tmp_path / "state.json"
    path.write_text('{"cookies": [], "origins": []}', encoding="utf-8")
    s = Settings(doubao_crawl_storage_state_path=str(path))
    with pytest.raises(DoubaoLoginExpired):
        load_storage_state(s)


def test_load_storage_state_ok(tmp_path: Path) -> None:
    path = tmp_path / "state.json"
    path.write_text(
        '{"cookies": [{"name": "sessionid", "value": "x", "domain": ".doubao.com", '
        '"path": "/", "expires": -1, "httpOnly": true, "secure": true, "sameSite": "Lax"}], '
        '"origins": []}',
        encoding="utf-8",
    )
    s = Settings(doubao_crawl_storage_state_path=str(path))
    data = load_storage_state(s)
    assert data is not None
    assert len(data["cookies"]) == 1
