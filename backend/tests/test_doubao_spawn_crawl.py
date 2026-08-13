"""Tests for Doubao crawl subprocess helper."""

from __future__ import annotations

import json
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


def test_run_doubao_crawl_in_subprocess(tmp_path, monkeypatch) -> None:
    payload = {"headless": True, "prompt": "hi", "storage_state": {"cookies": []}}

    def fake_run(cmd, **kwargs):
        # --out path is cmd[-1]
        out_path = cmd[cmd.index("--out") + 1]
        Path = __import__("pathlib").Path
        Path(out_path).write_text(
            json.dumps(
                {
                    "ok": True,
                    "text": "hi",
                    "latency_ms": 1,
                    "source_urls": [],
                    "search_queries": [],
                    "share_url": "",
                    "storage_state": {"cookies": []},
                }
            ),
            encoding="utf-8",
        )
        return MagicMock(returncode=0, stdout="", stderr="")

    with patch(
        "aperix_geo.services.providers.doubao_web.spawn_crawl.subprocess.run",
        side_effect=fake_run,
    ):
        out = run_doubao_crawl_in_spawn(payload, timeout_s=30)

    assert out["ok"] is True
    assert out["text"] == "hi"
