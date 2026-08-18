"""Tests for geo-web-crawl registry, client, spawn, and browser pool."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from aperix_geo.services.geo_web_crawl.client import run_geo_web_crawl_job
from aperix_geo.services.geo_web_crawl.jobs import _run_job_sync
from aperix_geo.services.geo_web_crawl.registry import (
    ensure_handlers_loaded,
    get_handler,
    list_platforms,
)
from aperix_geo.services.geo_web_crawl.spawn import run_geo_web_crawl_spawn


def test_registry_loads_platforms() -> None:
    ensure_handlers_loaded()
    assert "doubao" in list_platforms()
    assert "deepseek" in list_platforms()
    assert "qianwen" in list_platforms()
    assert get_handler("doubao") is not None


def test_deepseek_stub_handler() -> None:
    ensure_handlers_loaded()
    handler = get_handler("deepseek")
    assert handler is not None
    out = handler({"mode": "crawl"}, MagicMock(), MagicMock())
    assert out["ok"] is False
    assert out["error_type"] == "PlatformNotImplemented"


def test_run_job_sync_unknown_platform(monkeypatch) -> None:
    monkeypatch.delenv("GEO_CRAWL_PROFILE_ROOT", raising=False)
    out = _run_job_sync(
        {"platform": "nope", "storage_state": {"cookies": []}, "mode": "crawl"}
    )
    assert out["ok"] is False
    assert out["error_type"] == "PlatformNotImplemented"


def test_run_job_sync_doubao_probe(monkeypatch) -> None:
    monkeypatch.delenv("GEO_CRAWL_PROFILE_ROOT", raising=False)
    ensure_handlers_loaded()

    class _CM:
        def __enter__(self):
            return MagicMock(), MagicMock()

        def __exit__(self, *args):
            return False

    monkeypatch.setattr(
        "aperix_geo.services.geo_web_crawl.browser_pool.page_session",
        lambda **kwargs: _CM(),
    )
    monkeypatch.setattr(
        "aperix_geo.services.providers.doubao_web.jobs.probe.run_doubao_login_probe_on_page",
        lambda page, context, payload: {
            "ok": True,
            "storage_state": {"cookies": [{"name": "sessionid"}]},
            "error_type": "",
            "error": "",
            "human_ops": False,
        },
    )
    out = _run_job_sync(
        {
            "platform": "doubao",
            "mode": "probe",
            "storage_state": {"cookies": [{"name": "sessionid"}]},
        }
    )
    assert out["ok"] is True


def test_client_posts_job(monkeypatch) -> None:
    class _Resp:
        status_code = 200

        def json(self):
            return {"ok": True, "text": "hi", "storage_state": {"cookies": []}}

    class _Client:
        def __init__(self, *a, **k):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def post(self, url, json=None, headers=None):
            assert url.endswith("/v1/jobs")
            assert json["platform"] == "doubao"
            assert headers["Authorization"].startswith("Bearer ")
            return _Resp()

    monkeypatch.setattr("aperix_geo.services.geo_web_crawl.client.httpx.Client", _Client)
    out = run_geo_web_crawl_job(
        {"mode": "crawl", "storage_state": {"cookies": []}, "prompt": "x"},
        base_url="http://crawl:9410",
        token="secret",
        timeout_s=30,
    )
    assert out["ok"] is True
    assert out["text"] == "hi"


def test_spawn_prefers_http_base_url(monkeypatch) -> None:
    monkeypatch.setenv("GEO_WEB_CRAWL_BASE_URL", "http://127.0.0.1:9410")

    with patch(
        "aperix_geo.services.geo_web_crawl.client.run_geo_web_crawl_job",
        return_value={"ok": True, "text": "via-http"},
    ) as http_job:
        out = run_geo_web_crawl_spawn(
            {"prompt": "hi", "storage_state": {"cookies": []}},
            timeout_s=30,
        )
    assert out["ok"] is True
    assert out["text"] == "via-http"
    assert http_job.called
    assert http_job.call_args.kwargs.get("base_url") == "http://127.0.0.1:9410"
    assert http_job.call_args.args[0]["platform"] == "doubao"


def test_spawn_local_subprocess_when_no_base_url(monkeypatch) -> None:
    monkeypatch.delenv("GEO_WEB_CRAWL_BASE_URL", raising=False)

    def fake_run(cmd, **kwargs):
        out_path = cmd[cmd.index("--out") + 1]
        Path(out_path).write_text(
            json.dumps({"ok": True, "text": "local", "storage_state": {"cookies": []}}),
            encoding="utf-8",
        )
        return MagicMock(returncode=0, stdout="", stderr="")

    with patch(
        "aperix_geo.services.geo_web_crawl.spawn.subprocess.run",
        side_effect=fake_run,
    ):
        out = run_geo_web_crawl_spawn(
            {"prompt": "hi", "storage_state": {"cookies": []}},
            timeout_s=30,
        )
    assert out["ok"] is True
    assert out["text"] == "local"


def test_healthz_app() -> None:
    from fastapi.testclient import TestClient

    from aperix_geo.services.geo_web_crawl.server import create_app

    client = TestClient(create_app())
    resp = client.get("/healthz")
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert "doubao" in body["platforms"]
    assert body["browser_backend"] in {"local", "profile"}


def test_browser_backend_profile(monkeypatch) -> None:
    from aperix_geo.services.geo_web_crawl.browser_pool import browser_backend

    monkeypatch.delenv("GEO_CRAWL_PROFILE_ROOT", raising=False)
    assert browser_backend() == "local"
    monkeypatch.setenv("GEO_CRAWL_PROFILE_ROOT", "/data/crawl-profiles")
    assert browser_backend() == "profile"


def test_page_session_requires_ready_profile(tmp_path, monkeypatch) -> None:
    from aperix_geo.services.geo_web_crawl.browser_pool import page_session

    monkeypatch.setenv("GEO_CRAWL_PROFILE_ROOT", str(tmp_path))
    try:
        with page_session(
            storage_state={"cookies": []},
            timeout_ms=5000,
            account_id="11111111-1111-1111-1111-111111111111",
        ):
            raise AssertionError("expected missing profile")
    except RuntimeError as exc:
        assert "chrome profile missing" in str(exc)


def test_page_session_ephemeral_local(monkeypatch) -> None:
    from aperix_geo.services.geo_web_crawl import browser_pool

    monkeypatch.delenv("GEO_CRAWL_PROFILE_ROOT", raising=False)

    browser = MagicMock()
    context = MagicMock()
    page = MagicMock()
    browser.new_context.return_value = context
    context.new_page.return_value = page

    playwright = MagicMock()
    playwright.chromium.launch.return_value = browser

    pw_cm = MagicMock()
    pw_cm.start.return_value = playwright

    monkeypatch.setattr("playwright.sync_api.sync_playwright", lambda: pw_cm)

    with browser_pool.page_session(
        storage_state={"cookies": [{"name": "sessionid", "value": "x"}]},
        timeout_ms=5000,
        account_id="",
    ) as (got_page, got_ctx):
        assert got_page is page
        assert got_ctx is context

    playwright.chromium.launch.assert_called()
    context.close.assert_called()
    browser.close.assert_called()
