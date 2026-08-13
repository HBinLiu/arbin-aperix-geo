"""Tests for Doubao crawl spawn helper."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from aperix_geo.services.providers.doubao_web.spawn_crawl import (
    run_doubao_crawl_in_spawn,
    should_spawn_doubao_crawl,
)


def test_should_spawn_under_celery_role(monkeypatch) -> None:
    monkeypatch.delenv("DOUBAO_CRAWL_SUBPROCESS", raising=False)
    monkeypatch.setenv("CELERY_WORKER_ROLE", "llm")
    assert should_spawn_doubao_crawl() is True
    monkeypatch.delenv("CELERY_WORKER_ROLE", raising=False)
    assert should_spawn_doubao_crawl() is False


def test_should_spawn_env_override(monkeypatch) -> None:
    monkeypatch.setenv("CELERY_WORKER_ROLE", "llm")
    monkeypatch.setenv("DOUBAO_CRAWL_SUBPROCESS", "0")
    assert should_spawn_doubao_crawl() is False
    monkeypatch.setenv("DOUBAO_CRAWL_SUBPROCESS", "1")
    monkeypatch.delenv("CELERY_WORKER_ROLE", raising=False)
    assert should_spawn_doubao_crawl() is True


def test_run_doubao_crawl_in_spawn_recv(monkeypatch) -> None:
    parent = MagicMock()
    parent.poll.return_value = True
    parent.recv.return_value = {
        "ok": True,
        "text": "hi",
        "latency_ms": 1,
        "source_urls": [],
        "search_queries": [],
        "share_url": "",
        "storage_state": {"cookies": []},
    }
    child = MagicMock()
    proc = MagicMock()
    proc.is_alive.return_value = False

    ctx = MagicMock()
    ctx.Pipe.return_value = (parent, child)
    ctx.Process.return_value = proc

    with patch(
        "aperix_geo.services.providers.doubao_web.spawn_crawl.mp.get_context",
        return_value=ctx,
    ):
        out = run_doubao_crawl_in_spawn({"headless": True}, timeout_s=30)

    assert out["ok"] is True
    assert out["text"] == "hi"
    proc.start.assert_called_once()
    child.close.assert_called_once()
    parent.close.assert_called_once()
