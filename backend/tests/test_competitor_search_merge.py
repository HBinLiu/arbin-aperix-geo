"""Tests for SearXNG hit merge into competitor search pool."""

from __future__ import annotations

from unittest.mock import patch

from aperix_geo.services.competitor.search import _merge_hits_into_pool
from aperix_geo.services.competitor.types import SearchPool
from aperix_geo.services.searxng import SearchHit


@patch("aperix_geo.services.competitor.search.host_resolves", return_value=True)
def test_merge_keeps_media_article_hits_without_domain_pool(_mock_dns) -> None:
    pool = SearchPool(domains=[], hits=[], hit_by_domain={})
    hits = [
        SearchHit(
            title="GEO 科普",
            url="https://www.jianshu.com/p/abc",
            snippet="Profound 与 Otterly 是主流 GEO 平台",
            query="GEO 平台",
        ),
        SearchHit(
            title="Wise 跨境支付",
            url="https://wise.com/business",
            snippet="企业跨境收款",
            query="GEO 平台",
        ),
    ]

    added, skipped_domains, hits_added = _merge_hits_into_pool(
        pool,
        hits,
        self_domain="sheepgeo.com",
    )

    assert hits_added == 2
    assert len(pool.hits) == 2
    assert added == 1
    assert skipped_domains == 1
    assert "jianshu.com" not in pool.domains
    assert "wise.com" in pool.domains
