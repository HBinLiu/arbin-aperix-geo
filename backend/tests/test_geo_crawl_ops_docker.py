"""Tests for shared geo-crawl-ops docker session helpers."""

from __future__ import annotations

from unittest.mock import patch

from aperix_geo.config import Settings
from aperix_geo.services.geo_crawl_ops.docker_session import (
    build_complete_callback_url,
    build_login_url,
    geo_crawl_ops_ready,
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
        == "http://api:8000/api/v1/ops/doubao/tickets/complete-by-token"
    )
    assert (
        build_complete_callback_url(
            "http://api:8000/api/v1/ops/doubao/tickets/complete-by-token"
        )
        == "http://api:8000/api/v1/ops/doubao/tickets/complete-by-token"
    )


def test_spawn_ops_session_docker_flow() -> None:
    settings = Settings(
        geo_crawl_ops_novnc_base_url="https://ops.example",
        geo_crawl_ops_docker_image="aperix/geo-crawl-ops:latest",
        geo_crawl_ops_callback_base_url="http://api:8000",
    )
    calls: list[list[str]] = []

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
        raise AssertionError(args)

    with (
        patch(
            "aperix_geo.services.geo_crawl_ops.docker_session.docker_cli_available",
            return_value=True,
        ),
        patch(
            "aperix_geo.services.geo_crawl_ops.docker_session._run_docker",
            side_effect=fake_run,
        ),
    ):
        out = spawn_ops_session(
            ticket_token="tok_abc",
            platform="doubao",
            start_url="https://www.doubao.com/chat/",
            ttl_min=15,
            ops_reason="captcha",
            settings=settings,
        )

    assert out.container_id == "cid123"
    assert out.host_port == 60123
    assert out.login_url == "https://ops.example/?ticket=tok_abc"
    create = next(c for c in calls if c[:1] == ["create"])
    assert "GEO_CRAWL_OPS_COMPLETE_URL=http://api:8000/api/v1/ops/doubao/tickets/complete-by-token" in create
    assert "GEO_CRAWL_OPS_REASON=captcha" in create
    assert any(c[:1] == ["start"] for c in calls)


def test_spawn_default_reason_login_expired() -> None:
    settings = Settings(
        geo_crawl_ops_novnc_base_url="https://ops.example",
        geo_crawl_ops_docker_image="aperix/geo-crawl-ops:latest",
    )
    calls: list[list[str]] = []

    def fake_run(args: list[str], *, timeout_s: float = 60.0) -> str:
        calls.append(args)
        if args[:1] == ["rm"]:
            return ""
        if args[:1] == ["create"]:
            return "cid"
        if args[:1] == ["start"]:
            return "cid"
        if args[:1] == ["inspect"]:
            return "1"
        raise AssertionError(args)

    with (
        patch(
            "aperix_geo.services.geo_crawl_ops.docker_session.docker_cli_available",
            return_value=True,
        ),
        patch(
            "aperix_geo.services.geo_crawl_ops.docker_session._run_docker",
            side_effect=fake_run,
        ),
    ):
        spawn_ops_session(
            ticket_token="t",
            platform="doubao",
            start_url="https://www.doubao.com/chat/",
            ttl_min=15,
            settings=settings,
        )
    create = next(c for c in calls if c[:1] == ["create"])
    assert "GEO_CRAWL_OPS_REASON=login_expired" in create
