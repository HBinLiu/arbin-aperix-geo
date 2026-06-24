"""Tests for setup confirmed-competitor enrichment."""

from unittest.mock import patch

from aperix_geo.services.competitor.enrich import enrich_confirmed_competitors
from aperix_geo.services.competitor.types import SiteHead


@patch("aperix_geo.services.competitor.enrich.fetch_site_heads")
def test_enrich_confirmed_fills_summary_and_aliases(mock_heads) -> None:
    mock_heads.return_value = {
        "new.com": SiteHead(
            "new.com",
            "NewCo Platform",
            "新一代 GEO 工具",
            True,
            resolved_url="https://www.new.com/",
            brand_names=("NewCo", "NewCo AI"),
        ),
    }
    session = {
        "competitors": [
            {
                "domain": "wise.com",
                "website_url": "https://wise.com",
                "brand": "Wise",
                "aliases": ["TransferWise"],
            }
        ]
    }
    competitors = [
        {
            "domain": "new.com",
            "website_url": "",
            "brand": "new.com",
            "summary": "",
            "aliases": [],
        },
        {
            "domain": "aibase.com",
            "website_url": "https://geo.aibase.com/",
            "brand": "GEOBase",
            "summary": "",
            "aliases": [],
        },
        {
            "domain": "wise.com",
            "website_url": "https://wise.com",
            "brand": "Wise",
            "summary": "",
            "aliases": [],
        },
    ]

    out = enrich_confirmed_competitors(competitors, session=session)

    assert out[0]["brand"] == "new.com"
    assert out[0]["summary"] == "新一代 GEO 工具"
    assert "NewCo" in out[0]["aliases"]
    assert out[0]["website_url"] == "https://www.new.com/"
    assert out[1]["website_url"].rstrip("/") == "https://geo.aibase.com"
    assert out[2]["aliases"] == ["TransferWise"]
    assert out[2]["summary"] == ""
