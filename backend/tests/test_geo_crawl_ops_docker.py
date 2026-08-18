"""Tests for shared geo-crawl-ops docker session helpers."""

from __future__ import annotations

from unittest.mock import patch
from uuid import uuid4

import pytest

from aperix_geo.config import Settings
from aperix_geo.services.geo_crawl_ops.docker_session import (
    GeoCrawlOpsDockerError,
    build_complete_callback_url,
    build_login_url,
    geo_crawl_ops_ready,
    rewrite_callback_url_for_container,
    spawn_ops_session,
)


def test_geo_crawl_ops_ready() -> None:
    assert not geo_crawl_ops_ready(
        Settings(geo_crawl_ops_novnc_base_url="", geo_crawl_ops_docker_image="")
    )
    assert geo_crawl_ops_ready(
        Settings(
            geo_crawl_ops_novnc_base_url="https://ops.example",
            geo_crawl_ops_docker_image="aperix/geo-crawl-ops:latest",
        )
    )


def test_build_login_url_templates() -> None:
    assert (
        build_login_url("https://ops.example", ticket_token="abc")
        == "https://ops.example/?ticket=abc"
    )
    assert (
        build_login_url("https://h:{port}/t/{ticket}", ticket_token="tok", host_port=60123)
        == "https://h:60123/t/tok"
    )


def test_build_complete_callback_url() -> None:
    assert build_complete_callback_url("") == ""
    assert (
        build_complete_callback_url("http://api:8000")
        == "http://api:8000/api/v1/ops/geo-crawl/tickets/complete-by-token"
    )
    assert (
        build_complete_callback_url(
            "http://api:8000/api/v1/ops/geo-crawl/tickets/complete-by-token"
        )
        == "http://api:8000/api/v1/ops/geo-crawl/tickets/complete-by-token"
    )


def test_rewrite_callback_url_for_container() -> None:
    url, need = rewrite_callback_url_for_container(
        "http://127.0.0.1:8000/api/v1/ops/geo-crawl/tickets/complete-by-token"
    )
    assert url.startswith("http://host.docker.internal:8000/")
    assert need is True
    url2, need2 = rewrite_callback_url_for_container(
        "http://api:8000/api/v1/ops/geo-crawl/tickets/complete-by-token"
    )
    assert url2.startswith("http://api:8000/")
    assert need2 is False


def _fake_docker(calls: list[list[str]]):
    def fake_run(args: list[str], *, timeout_s: float = 60.0) -> str:
        calls.append(args)
        if args[:1] == ["rm"]:
            return ""
        if args[:1] == ["create"]:
            return "cid123"
        if args[:1] == ["start"]:
            return "cid123"
        if args[:1] == ["inspect"]:
            return "60123"
        if args[:1] == ["cp"]:
            return ""
        raise AssertionError(args)

    return fake_run


def test_spawn_ops_session_requires_profile() -> None:
    settings = Settings(
        geo_crawl_ops_novnc_base_url="https://ops.example",
        geo_crawl_ops_docker_image="aperix/geo-crawl-ops:latest",
    )
    with (
        patch(
            "aperix_geo.services.geo_crawl_ops.docker_session.docker_cli_available",
            return_value=True,
        ),
        pytest.raises(GeoCrawlOpsDockerError, match="GEO_CRAWL_PROFILE_ROOT"),
    ):
        spawn_ops_session(
            ticket_token="tok_abc",
            platform="doubao",
            start_url="https://www.doubao.com/chat/",
            ttl_min=15,
            settings=settings,
        )


def test_spawn_ops_session_docker_flow(tmp_path) -> None:
    settings = Settings(
        geo_crawl_ops_novnc_base_url="https://ops.example",
        geo_crawl_ops_docker_image="aperix/geo-crawl-ops:latest",
        geo_crawl_ops_callback_base_url="http://api:8000",
        geo_crawl_profile_root=str(tmp_path),
    )
    calls: list[list[str]] = []
    account_id = str(uuid4())

    with (
        patch(
            "aperix_geo.services.geo_crawl_ops.docker_session.docker_cli_available",
            return_value=True,
        ),
        patch(
            "aperix_geo.services.geo_crawl_ops.docker_session._run_docker",
            side_effect=_fake_docker(calls),
        ),
    ):
        out = spawn_ops_session(
            ticket_token="tok_abc",
            platform="doubao",
            start_url="https://www.doubao.com/chat/",
            ttl_min=15,
            ops_reason="captcha",
            settings=settings,
            account_id=account_id,
        )

    assert out.container_id == "cid123"
    assert out.host_port == 60123
    assert out.login_url == "https://ops.example/?ticket=tok_abc"
    create = next(c for c in calls if c[:1] == ["create"])
    assert "--rm" in create
    assert "GEO_CRAWL_OPS_COMPLETE_URL=http://api:8000/api/v1/ops/geo-crawl/tickets/complete-by-token" in create
    assert "GEO_CRAWL_OPS_REASON=captcha" in create
    assert "GEO_CRAWL_OPS_PROFILE_DIR=/data/chrome-profile" in create
    assert any(str(tmp_path) in arg for arg in create)
    assert "--add-host" not in create
    assert any(c[:1] == ["start"] for c in calls)


def test_spawn_rewrites_loopback_callback(tmp_path) -> None:
    settings = Settings(
        geo_crawl_ops_novnc_base_url="https://ops.example",
        geo_crawl_ops_docker_image="aperix/geo-crawl-ops:latest",
        geo_crawl_ops_callback_base_url="http://127.0.0.1:8000",
        geo_crawl_profile_root=str(tmp_path),
    )
    calls: list[list[str]] = []

    with (
        patch(
            "aperix_geo.services.geo_crawl_ops.docker_session.docker_cli_available",
            return_value=True,
        ),
        patch(
            "aperix_geo.services.geo_crawl_ops.docker_session._run_docker",
            side_effect=_fake_docker(calls),
        ),
    ):
        spawn_ops_session(
            ticket_token="t",
            platform="doubao",
            start_url="https://www.doubao.com/chat/",
            ttl_min=15,
            settings=settings,
            account_id=str(uuid4()),
        )
    create = next(c for c in calls if c[:1] == ["create"])
    assert (
        "GEO_CRAWL_OPS_COMPLETE_URL="
        "http://host.docker.internal:8000/api/v1/ops/geo-crawl/tickets/complete-by-token"
        in create
    )
    assert create[create.index("--add-host") + 1] == "host.docker.internal:host-gateway"


def test_spawn_default_reason_login_expired(tmp_path) -> None:
    settings = Settings(
        geo_crawl_ops_novnc_base_url="https://ops.example",
        geo_crawl_ops_docker_image="aperix/geo-crawl-ops:latest",
        geo_crawl_profile_root=str(tmp_path),
    )
    calls: list[list[str]] = []

    with (
        patch(
            "aperix_geo.services.geo_crawl_ops.docker_session.docker_cli_available",
            return_value=True,
        ),
        patch(
            "aperix_geo.services.geo_crawl_ops.docker_session._run_docker",
            side_effect=_fake_docker(calls),
        ),
    ):
        spawn_ops_session(
            ticket_token="t",
            platform="doubao",
            start_url="https://www.doubao.com/chat/",
            ttl_min=15,
            settings=settings,
            account_id=str(uuid4()),
        )
    create = next(c for c in calls if c[:1] == ["create"])
    assert "GEO_CRAWL_OPS_REASON=login_expired" in create
