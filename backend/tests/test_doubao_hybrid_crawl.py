"""Hybrid transport orchestration (mocked spawn / web_http)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from aperix_geo.config import Settings
from aperix_geo.services.providers.doubao_web.errors import DoubaoLoginExpired
from aperix_geo.services.providers.doubao_web.hybrid_crawl import hybrid_crawl_doubao_chat
from aperix_geo.services.providers.result import SamplingChatResult


def _settings() -> Settings:
    return Settings(
        doubao_web_http_enabled=True,
        doubao_crawl_transport="hybrid",
        doubao_crawl_storage_state_path="",
        doubao_crawl_timeout_s=60,
    )


@patch("aperix_geo.db.session.SessionLocal")
@patch("aperix_geo.services.crawl_browser.client.run_crawl_job")
@patch("aperix_geo.services.providers.doubao_web.hybrid_crawl.complete_web_http")
@patch(
    "aperix_geo.services.providers.doubao_web.accounts.load_storage_state_from_file"
)
def test_hybrid_success(mock_load, mock_http, mock_spawn, mock_db):
    mock_load.return_value = {"cookies": [{"name": "sessionid", "value": "x"}]}
    mock_http.return_value = {
        "ok": True,
        "text": "正文",
        "search_queries": ["q1"],
        "source_urls": ["https://ex.example/a"],
        "conversation_id": "cid-1",
        "storage_state": {"cookies": [{"name": "sessionid", "value": "y"}]},
    }
    mock_spawn.return_value = {
        "ok": True,
        "share_url": "https://www.doubao.com/bot/chat/share?s=abc",
        "storage_state": {"cookies": [{"name": "sessionid", "value": "z"}]},
    }
    mock_db.return_value = MagicMock()

    result = hybrid_crawl_doubao_chat(
        [{"role": "user", "content": "hi"}],
        settings=_settings(),
        use_account_pool=False,
    )
    assert isinstance(result, SamplingChatResult)
    assert result.text == "正文"
    assert result.share_url.endswith("abc")
    assert result.search_queries == ("q1",)
    mock_spawn.assert_called_once()
    assert mock_spawn.call_args.kwargs.get("mode") == "share"


@patch("aperix_geo.db.session.SessionLocal")
@patch("aperix_geo.services.crawl_browser.client.run_crawl_job")
@patch("aperix_geo.services.providers.doubao_web.hybrid_crawl.complete_web_http")
@patch(
    "aperix_geo.services.providers.doubao_web.accounts.load_storage_state_from_file"
)
def test_hybrid_share_failure_keeps_http_body(mock_load, mock_http, mock_spawn, mock_db):
    mock_load.return_value = {"cookies": [{"name": "sessionid", "value": "x"}]}
    mock_http.return_value = {
        "ok": True,
        "text": "正文",
        "search_queries": [],
        "source_urls": [],
        "conversation_id": "cid-1",
        "storage_state": {"cookies": []},
    }
    mock_spawn.return_value = {
        "ok": False,
        "error_type": "DoubaoShareError",
        "error": "no share",
        "human_ops": False,
    }
    mock_db.return_value = MagicMock()

    result = hybrid_crawl_doubao_chat(
        [{"role": "user", "content": "hi"}],
        settings=_settings(),
        use_account_pool=False,
    )
    assert isinstance(result, SamplingChatResult)
    assert result.text == "正文"
    assert result.share_url == ""
    share_payload = mock_spawn.call_args[0][0]
    names = {c.get("name") for c in share_payload["storage_state"]["cookies"]}
    assert "sessionid" in names


@patch("aperix_geo.db.session.SessionLocal")
@patch("aperix_geo.services.crawl_browser.client.run_crawl_job")
@patch("aperix_geo.services.providers.doubao_web.hybrid_crawl.complete_web_http")
@patch(
    "aperix_geo.services.providers.doubao_web.accounts.load_storage_state_from_file"
)
def test_hybrid_share_human_ops_still_fails(mock_load, mock_http, mock_spawn, mock_db):
    mock_load.return_value = {"cookies": [{"name": "sessionid", "value": "x"}]}
    mock_http.return_value = {
        "ok": True,
        "text": "正文",
        "search_queries": [],
        "source_urls": [],
        "conversation_id": "cid-1",
        "storage_state": {"cookies": []},
    }
    mock_spawn.return_value = {
        "ok": False,
        "error_type": "DoubaoLoginExpired",
        "error": "redirected to login",
        "human_ops": True,
    }
    mock_db.return_value = MagicMock()

    with pytest.raises(DoubaoLoginExpired):
        hybrid_crawl_doubao_chat(
            [{"role": "user", "content": "hi"}],
            settings=_settings(),
            use_account_pool=False,
        )
