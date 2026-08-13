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
from aperix_geo.services.geo_web_crawl.spawn import (
    resolve_geo_web_crawl_docker_image,
    run_geo_web_crawl_spawn,
    should_use_geo_web_crawl_docker,
)


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


def test_run_job_sync_unknown_platform() -> None:
    out = _run_job_sync(
        {"platform": "nope", "storage_state": {"cookies": []}, "mode": "crawl"}
    )
    assert out["ok"] is False
    assert out["error_type"] == "PlatformNotImplemented"


def test_run_job_sync_doubao_probe(monkeypatch) -> None:
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
        "aperix_geo.services.providers.doubao_web.probe_job.run_doubao_login_probe_on_page",
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


def test_docker_image_resolution(monkeypatch) -> None:
    monkeypatch.delenv("GEO_WEB_CRAWL_DOCKER_IMAGE", raising=False)
    assert resolve_geo_web_crawl_docker_image("") == ""
    assert should_use_geo_web_crawl_docker() is False
    monkeypatch.setenv("GEO_WEB_CRAWL_DOCKER_IMAGE", "aperix/geo-web-crawl:latest")
    assert resolve_geo_web_crawl_docker_image() == "aperix/geo-web-crawl:latest"
    assert should_use_geo_web_crawl_docker() is True
    assert resolve_geo_web_crawl_docker_image("custom:tag") == "custom:tag"


def test_spawn_prefers_http_base_url(monkeypatch) -> None:
    monkeypatch.setenv("GEO_WEB_CRAWL_BASE_URL", "http://127.0.0.1:9410")
    monkeypatch.delenv("GEO_WEB_CRAWL_DOCKER_EPHEMERAL", raising=False)

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
    monkeypatch.delenv("GEO_WEB_CRAWL_DOCKER_IMAGE", raising=False)
    monkeypatch.delenv("GEO_WEB_CRAWL_DOCKER_EPHEMERAL", raising=False)

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


def test_ephemeral_docker_when_enabled(monkeypatch) -> None:
    monkeypatch.delenv("GEO_WEB_CRAWL_BASE_URL", raising=False)
    monkeypatch.setenv("GEO_WEB_CRAWL_DOCKER_IMAGE", "aperix/geo-web-crawl:test")
    monkeypatch.setenv("GEO_WEB_CRAWL_DOCKER_EPHEMERAL", "1")
    payload = {"headless": True, "prompt": "hi", "storage_state": {"cookies": []}}

    def fake_run(cmd, **kwargs):
        assert cmd[0] == "docker"
        assert "run" in cmd
        assert "--shm-size=1g" in cmd
        assert "aperix/geo-web-crawl:test" in cmd
        vol = next(x for x in cmd if isinstance(x, str) and x.endswith(":/data"))
        host_dir = Path(vol.split(":", 1)[0])
        (host_dir / "out.json").write_text(
            json.dumps({"ok": True, "text": "from-docker", "storage_state": {"cookies": []}}),
            encoding="utf-8",
        )
        return MagicMock(returncode=0, stdout="", stderr="")

    with (
        patch(
            "aperix_geo.services.geo_web_crawl.spawn.shutil.which",
            return_value="/usr/bin/docker",
        ),
        patch(
            "aperix_geo.services.geo_web_crawl.spawn.subprocess.run",
            side_effect=fake_run,
        ),
    ):
        out = run_geo_web_crawl_spawn(payload, timeout_s=30)

    assert out["ok"] is True
    assert out["text"] == "from-docker"


def test_ephemeral_docker_missing_cli(monkeypatch) -> None:
    monkeypatch.delenv("GEO_WEB_CRAWL_BASE_URL", raising=False)
    monkeypatch.setenv("GEO_WEB_CRAWL_DOCKER_IMAGE", "aperix/geo-web-crawl:test")
    monkeypatch.setenv("GEO_WEB_CRAWL_DOCKER_EPHEMERAL", "1")
    with patch(
        "aperix_geo.services.geo_web_crawl.spawn.shutil.which",
        return_value=None,
    ):
        out = run_geo_web_crawl_spawn(
            {"prompt": "x", "storage_state": {"cookies": []}},
            timeout_s=10,
        )
    assert out["ok"] is False
    assert "docker CLI not found" in out["error"]


def test_ephemeral_docker_probe_mode(monkeypatch) -> None:
    monkeypatch.delenv("GEO_WEB_CRAWL_BASE_URL", raising=False)
    monkeypatch.setenv("GEO_WEB_CRAWL_DOCKER_IMAGE", "aperix/geo-web-crawl:test")
    monkeypatch.setenv("GEO_WEB_CRAWL_DOCKER_EPHEMERAL", "1")

    def fake_run(cmd, **kwargs):
        assert "--mode" in cmd
        assert cmd[cmd.index("--mode") + 1] == "probe"
        vol = next(x for x in cmd if isinstance(x, str) and x.endswith(":/data"))
        host_dir = Path(vol.split(":", 1)[0])
        (host_dir / "out.json").write_text(
            json.dumps(
                {
                    "ok": True,
                    "storage_state": {"cookies": [{"name": "sessionid"}]},
                    "error_type": "",
                    "error": "",
                    "human_ops": False,
                }
            ),
            encoding="utf-8",
        )
        return MagicMock(returncode=0, stdout="", stderr="")

    with (
        patch(
            "aperix_geo.services.geo_web_crawl.spawn.shutil.which",
            return_value="/usr/bin/docker",
        ),
        patch(
            "aperix_geo.services.geo_web_crawl.spawn.subprocess.run",
            side_effect=fake_run,
        ),
    ):
        out = run_geo_web_crawl_spawn(
            {"storage_state": {"cookies": [{"name": "sessionid"}]}},
            timeout_s=30,
            mode="probe",
        )
    assert out["ok"] is True
    assert out["storage_state"]["cookies"]


def test_healthz_app() -> None:
    from fastapi.testclient import TestClient

    from aperix_geo.services.geo_web_crawl.server import create_app

    client = TestClient(create_app())
    resp = client.get("/healthz")
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert "doubao" in body["platforms"]
    assert body["browser_backend"] in {"local", "browserless"}


def test_resolve_browser_ws_url_appends_token(monkeypatch) -> None:
    from aperix_geo.services.geo_web_crawl.browser_pool import (
        browser_backend,
        resolve_browser_ws_url,
    )

    monkeypatch.delenv("GEO_WEB_CRAWL_BROWSER_WS_URL", raising=False)
    assert resolve_browser_ws_url() == ""
    assert browser_backend() == "local"

    monkeypatch.setenv(
        "GEO_WEB_CRAWL_BROWSER_WS_URL",
        "ws://browserless:3000/chromium/playwright",
    )
    monkeypatch.setenv("GEO_WEB_CRAWL_BROWSERLESS_TOKEN", "secret")
    url = resolve_browser_ws_url()
    assert "token=secret" in url
    assert browser_backend() == "browserless"


def test_page_session_browserless_connect(monkeypatch) -> None:
    from aperix_geo.services.geo_web_crawl import browser_pool

    monkeypatch.setenv(
        "GEO_WEB_CRAWL_BROWSER_WS_URL",
        "ws://browserless:3000/chromium/playwright?token=t",
    )

    browser = MagicMock()
    context = MagicMock()
    page = MagicMock()
    browser.new_context.return_value = context
    context.new_page.return_value = page

    playwright = MagicMock()
    playwright.chromium.connect.return_value = browser
    playwright.chromium.connect_over_cdp.return_value = browser

    pw_cm = MagicMock()
    pw_cm.start.return_value = playwright

    monkeypatch.setattr(
        "playwright.sync_api.sync_playwright",
        lambda: pw_cm,
    )

    with browser_pool.page_session(
        storage_state={"cookies": []},
        timeout_ms=5000,
    ) as (got_page, got_ctx):
        assert got_page is page
        assert got_ctx is context

    assert playwright.chromium.connect.called
    assert not playwright.chromium.connect_over_cdp.called
    context.close.assert_called()
    browser.close.assert_called()
