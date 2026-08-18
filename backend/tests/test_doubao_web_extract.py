"""Unit tests for Doubao Web panel extraction / md-box HTML → Markdown."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from aperix_geo.config import Settings
from aperix_geo.services.providers.doubao_web.accounts import (
    load_storage_state_from_file,
    resolve_storage_state_path,
)
from aperix_geo.services.providers.doubao_web.crawler import user_prompt_from_messages
from aperix_geo.services.providers.doubao_web.errors import DoubaoLoginExpired
from aperix_geo.services.providers.doubao_web.extract import (
    blank_chat_failure_reason,
    clean_assistant_text,
    conversation_id_from_url,
    extract_quoted_queries,
    extract_urls,
    filter_http_urls,
    md_box_html_to_markdown,
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

SAMPLE_MD_BOX = """
<div class="container-h3Yzeb">
  <div data-streaming="false" class="container-qX9Csx md-box-root">
    <div class="container-fBOrXO"><h1 class="container-KCOKpE">面向抖音网红的 SaaS 方向</h1></div>
    <div class="container-fBOrXO"><blockquote class="container-U80Nkv">
      <div class="container-enLQFx">核心原则：<strong class="container-nB6Z1e">博主愿意付费</strong></div>
    </blockquote></div>
    <div class="container-fBOrXO"><div class="container-enLQFx">结合前面分析分成 6 大类。</div></div>
    <div class="container-fBOrXO"><h2 class="container-KCOKpE">第一大类：直播辅助</h2></div>
    <div class="container-fBOrXO"><ol class="container-RLBpOb">
      <li>实时违禁词预警；</li>
      <li>话术复盘。</li>
    </ol></div>
    <div class="container-fBOrXO"><table><thead><tr><th>困境</th><th>工具</th></tr></thead>
      <tbody><tr><td>合规风险</td><td>预审复盘</td></tr></tbody></table></div>
  </div>
</div>
"""


def test_conversation_id_from_url() -> None:
    assert conversation_id_from_url("https://www.doubao.com/chat/") == ""
    assert conversation_id_from_url("https://www.doubao.com/chat") == ""
    assert (
        conversation_id_from_url("https://www.doubao.com/chat/xmOWWDyV4wJ6gt49W")
        == "xmOWWDyV4wJ6gt49W"
    )
    assert (
        conversation_id_from_url("https://www.doubao.com/chat/abc-123_xyz/extra")
        == "abc-123_xyz"
    )


def test_blank_chat_failure_reason() -> None:
    assert (
        blank_chat_failure_reason(
            url="https://www.doubao.com/chat/",
            md_box_texts=[],
            message_like_count=0,
            search_panel_hint=False,
            prior_conversation_id="oldid123",
        )
        == ""
    )
    assert "prior conversation" in blank_chat_failure_reason(
        url="https://www.doubao.com/chat/oldid123",
        md_box_texts=[],
        message_like_count=0,
        search_panel_hint=False,
        prior_conversation_id="oldid123",
    )
    assert "md-box history" in blank_chat_failure_reason(
        url="https://www.doubao.com/chat/",
        md_box_texts=["已有助手回复"],
        message_like_count=0,
        search_panel_hint=False,
    )
    assert "search panel" in blank_chat_failure_reason(
        url="https://www.doubao.com/chat/",
        md_box_texts=[],
        message_like_count=0,
        search_panel_hint=True,
    )
    assert "message-like" in blank_chat_failure_reason(
        url="https://www.doubao.com/chat/",
        md_box_texts=[],
        message_like_count=5,
        search_panel_hint=False,
    )


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


def test_filter_http_urls_keeps_absolute_http() -> None:
    urls = filter_http_urls(
        [
            "https://example.com/a",
            "https://www.doubao.com/algo/redirect?u=1",
            "/relative",
            "javascript:void(0)",
            "",
        ]
    )
    assert "https://example.com/a" in urls
    assert "https://www.doubao.com/algo/redirect?u=1" in urls
    assert "/relative" not in urls


def test_page_looks_like_captcha() -> None:
    from aperix_geo.services.providers.doubao_web.extract import page_looks_like_captcha

    assert page_looks_like_captcha("请选择所有符合上文描述的图片，并拖拽到下方\n拖拽到这里")
    assert page_looks_like_captcha("请完成行为验证后继续")
    assert page_looks_like_captcha("当前环境异常，请换个网络后再试")
    assert not page_looks_like_captcha("适合小团队的 CRM 有哪些\nZoho CRM 推荐")


def test_md_box_html_to_markdown_keeps_structure() -> None:
    md = md_box_html_to_markdown(SAMPLE_MD_BOX)
    assert md.startswith("# 面向抖音网红的 SaaS 方向")
    assert "## 第一大类：直播辅助" in md
    assert "> 核心原则：" in md
    assert "**博主愿意付费**" in md
    assert "1. 实时违禁词预警" in md
    assert "| 困境 | 工具 |" in md
    assert "搜索" not in md
    assert "下载电脑版" not in md


def test_clean_assistant_text_preserves_markdown() -> None:
    md = md_box_html_to_markdown(SAMPLE_MD_BOX)
    cleaned = clean_assistant_text(md, user_prompt="随便问一句")
    assert cleaned.startswith("# 面向抖音网红的 SaaS 方向")
    assert "## 第一大类" in cleaned


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
        load_storage_state_from_file(s)


def test_load_storage_state_ok(tmp_path: Path) -> None:
    path = tmp_path / "state.json"
    path.write_text(
        '{"cookies": [{"name": "sessionid", "value": "x", "domain": ".doubao.com", '
        '"path": "/", "expires": -1, "httpOnly": true, "secure": true, "sameSite": "Lax"}], '
        '"origins": []}',
        encoding="utf-8",
    )
    s = Settings(doubao_crawl_storage_state_path=str(path))
    data = load_storage_state_from_file(s)
    assert data is not None
    assert len(data["cookies"]) == 1


def test_load_storage_state_rejects_guest_cookies(tmp_path: Path) -> None:
    path = tmp_path / "state.json"
    path.write_text(
        '{"cookies": [{"name": "odin_tt", "value": "guest", "domain": ".doubao.com", '
        '"path": "/", "expires": -1, "httpOnly": false, "secure": true, "sameSite": "Lax"}]}',
        encoding="utf-8",
    )
    s = Settings(doubao_crawl_storage_state_path=str(path))
    with pytest.raises(DoubaoLoginExpired, match="session cookies"):
        load_storage_state_from_file(s)


@patch("aperix_geo.services.providers.doubao_web.accounts.load_storage_state_from_file")
@patch("aperix_geo.services.crawl_accounts.pool.acquire_account", return_value=None)
def test_pool_acquire_does_not_fall_back_to_file(mock_acquire, mock_file) -> None:
    from aperix_geo.services.providers.doubao_web.accounts import DoubaoCredentialSession
    from aperix_geo.services.providers.doubao_web.errors import DoubaoCrawlError

    session = DoubaoCredentialSession(db=MagicMock(), settings=Settings())
    with pytest.raises(DoubaoCrawlError, match="pool empty"):
        session.acquire(use_account_pool=True)
    mock_file.assert_not_called()
    mock_acquire.assert_called_once()
