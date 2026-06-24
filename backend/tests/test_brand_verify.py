"""Tests for brand domain homepage verification."""

from __future__ import annotations

from unittest.mock import patch

from aperix_geo.services.brand.verify import (
    accept_discovered_domain,
    homepage_matches_both_brands,
    site_head_matches_brand,
    verify_domain_homepage,
)
from aperix_geo.services.competitor.types import SiteHead


def test_site_head_matches_latin_brand_in_title() -> None:
    head = SiteHead("stripe.com", "Stripe | Payments", "", True)
    assert site_head_matches_brand(head, "Stripe")


def test_site_head_matches_cjk_segment_in_title() -> None:
    head = SiteHead("guangyinai.com", "光引AI - 官网", "", True)
    assert site_head_matches_brand(head, "光引GEO")


def test_site_head_rejects_unreachable() -> None:
    head = SiteHead("sohu.com", "DeepRank 评测", "", False)
    assert not site_head_matches_brand(head, "DeepRank")


@patch("aperix_geo.services.brand.verify.verify_domain_homepage", return_value=False)
@patch("aperix_geo.services.brand.verify.registrable_domain", return_value=True)
def test_accept_discovered_domain_host_match_skips_homepage(
    _mock_dns: object,
    mock_homepage: object,
) -> None:
    assert accept_discovered_domain("stripe.com", "Stripe")
    mock_homepage.assert_not_called()


def test_homepage_matches_both_brands() -> None:
    head = SiteHead(
        "wise.com",
        "Wise | TransferWise 跨境汇款",
        "",
        True,
        brand_names=("TransferWise",),
    )
    assert homepage_matches_both_brands("wise.com", "TransferWise", "Wise", head=head)


def test_homepage_matches_both_brands_rejects_single_name() -> None:
    head = SiteHead("zgswcn.com", "透镜GEO 官网", "", True)
    assert not homepage_matches_both_brands("zgswcn.com", "智瞰引擎", "透镜GEO", head=head)


@patch("aperix_geo.services.brand.verify.fetch_site_heads")
@patch("aperix_geo.services.brand.verify.registrable_domain", return_value=True)
def test_verify_domain_homepage_uses_head_fetch(mock_dns: object, mock_fetch: object) -> None:
    mock_fetch.return_value = {
        "paypal.com": SiteHead("paypal.com", "贝宝中国", "", True),
    }
    assert verify_domain_homepage("paypal.com", "贝宝")
    mock_fetch.assert_called_once()
