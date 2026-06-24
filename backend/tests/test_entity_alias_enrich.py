"""Tests for shared subject / open-set alias enrichment."""

from aperix_geo.services.competitor.enrich import enrich_entity_aliases, enrich_open_set_brand_aliases
from aperix_geo.services.competitor.types import SiteHead
from aperix_geo.services.setup.helpers import enrich_subject_aliases


def test_enrich_subject_aliases_from_site_data_title() -> None:
    session = {
        "target": "wise.com",
        "profile": {"company": "Wise"},
        "research_payload": {
            "mode": "domain",
            "site_data": {"title": "万里汇 | 跨境支付平台", "description": "跨境汇款"},
        },
    }
    aliases = enrich_subject_aliases(
        brand="Wise",
        domain="wise.com",
        website_url="https://wise.com",
        session=session,
    )
    assert "万里汇" in aliases
    assert "Wise" not in aliases


def test_enrich_entity_aliases_from_head() -> None:
    head = SiteHead(
        "stripe.com",
        "Stripe | 全球支付",
        "支付平台",
        True,
        brand_names=("Stripe Payments",),
    )
    aliases = enrich_entity_aliases(
        brand="Stripe",
        domain="stripe.com",
        existing=["Stripe Inc"],
        head=head,
    )
    assert "Stripe Inc" in aliases
    assert "Stripe Payments" in aliases


def test_enrich_open_set_brand_aliases() -> None:
    head = SiteHead(
        "wise.com",
        "万里汇 | Wise",
        "跨境汇款",
        True,
        brand_names=("TransferWise",),
    )
    aliases = enrich_open_set_brand_aliases(
        brand="Wise",
        domain="wise.com",
        existing=[],
        head=head,
    )
    assert "万里汇" in aliases
    assert "TransferWise" in aliases
