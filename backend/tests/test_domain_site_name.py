"""Tests for homepage-based domain site_name resolution."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

from aperix_geo.services.domain.site_name import fetch_site_name_from_homepage


def test_fetch_site_name_from_homepage_uses_home_url_not_article() -> None:
    fetch_urls: list[str] = []

    def fake_fetch(url: str, **kwargs):
        fetch_urls.append(url)
        return SimpleNamespace(fetch_ok=True, html="<html></html>", markdown="", final_url=url)

    parsed = SimpleNamespace(
        site_name="万里汇",
        publisher="",
        breadcrumbs=[],
        title="跨境支付平台",
    )

    with (
        patch("aperix_geo.services.domain.site_name.fetch_page", side_effect=fake_fetch),
        patch(
            "aperix_geo.services.domain.site_name.extract_metadata_from_fetch",
            return_value=parsed,
        ),
        patch(
            "aperix_geo.services.domain.site_name.homepage_url_candidates",
            return_value=["https://www.wise.com/", "https://wise.com/"],
        ),
    ):
        name = fetch_site_name_from_homepage("blog.wise.com")

    assert name == "万里汇"
    assert fetch_urls[0] == "https://www.wise.com/"
    assert all("/blog/" not in u for u in fetch_urls)
