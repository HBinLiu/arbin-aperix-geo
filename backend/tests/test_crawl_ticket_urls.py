"""Tests for crawl login ticket URL helpers."""

from __future__ import annotations

from aperix_geo.services.crawl_accounts.ticket_urls import (
    advertised_vnc_port,
    build_complete_callback_url,
    build_login_url,
    rewrite_loopback_callback_url,
)


def test_build_login_url_templates() -> None:
    assert (
        build_login_url("https://ops.example", ticket_token="abc")
        == "https://ops.example/?ticket=abc"
    )
    assert (
        build_login_url(
            "https://h:{port}/t/{ticket}", ticket_token="tok", host_port=6091
        )
        == "https://h:6091/t/tok"
    )
    assert advertised_vnc_port("6091") == 6091
    assert advertised_vnc_port(0) == 0
    assert advertised_vnc_port("nope") == 0


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


def test_rewrite_loopback_callback_url() -> None:
    url = rewrite_loopback_callback_url(
        "http://127.0.0.1:8000/api/v1/ops/geo-crawl/tickets/complete-by-token"
    )
    assert url.startswith("http://host.docker.internal:8000/")
    url2 = rewrite_loopback_callback_url(
        "http://api:8000/api/v1/ops/geo-crawl/tickets/complete-by-token"
    )
    assert url2.startswith("http://api:8000/")
