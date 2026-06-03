"""Tests for packaging discovered competitors."""

from unittest.mock import patch

from aperix_geo.services.competitor.output import package_discovered_competitors
from aperix_geo.services.competitor.types import SiteHead


@patch("aperix_geo.services.competitor.output.host_resolves", return_value=True)
def test_package_reuses_heads(_mock_dns) -> None:
    heads = {
        "wise.com": SiteHead("wise.com", "万里汇 | 跨境支付", "desc", True),
        "paypal.com": SiteHead("paypal.com", "", "", False),
    }
    out = package_discovered_competitors(
        ["business.wise.com", "www.wise.com", "paypal.com"],
        heads,
    )
    assert len(out) == 1
    assert out[0]["domain"] == "wise.com"
    assert out[0]["site_name"] == "万里汇"


@patch("aperix_geo.services.competitor.output.host_resolves", return_value=True)
def test_package_backfills_when_top_unreachable(_mock_dns) -> None:
    heads = {
        "bad.com": SiteHead("bad.com", "Bad", "desc", False),
        "good-a.com": SiteHead("good-a.com", "Good A", "desc", True),
        "good-b.com": SiteHead("good-b.com", "Good B", "desc", True),
    }
    out = package_discovered_competitors(
        ["bad.com", "good-a.com", "good-b.com"],
        heads,
        max_items=2,
    )
    assert [c["domain"] for c in out] == ["good-a.com", "good-b.com"]
