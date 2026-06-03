"""将主域名短名单打包为 API 响应（可打开 + 中文站名）。"""

from __future__ import annotations

import logging

from aperix_geo.services.competitor.defaults import (
    METADATA_CONCURRENCY,
    METADATA_TIMEOUT_S,
    RESULT_MAX,
    RESULT_MIN,
)
from aperix_geo.utils.domains import registrable_domain, site_name_from_title
from aperix_geo.services.competitor.head_fetch import fetch_site_heads
from aperix_geo.services.competitor.types import DiscoveredCompetitor, SiteHead
from aperix_geo.utils.url import host_resolves

logger = logging.getLogger(__name__)


def _should_try_domain(domain: str, heads: dict[str, SiteHead]) -> bool:
    """已有 head 时以 HTTP 可达为准，避免重复 DNS 且与交叉验算结论一致。"""
    head = heads.get(domain)
    if head is not None:
        return head.reachable
    return host_resolves(domain)


def package_discovered_competitors(
    domain_order: list[str],
    heads: dict[str, SiteHead],
    *,
    min_items: int | None = None,
    max_items: int | None = None,
) -> list[DiscoveredCompetitor]:
    """主域名去重、可达校验、提取中文站点名（复用交叉验算已抓取的 heads）。"""
    min_items = min_items if min_items is not None else RESULT_MIN
    max_items = max_items if max_items is not None else RESULT_MAX

    ordered = list(dict.fromkeys(registrable_domain(d) for d in domain_order if d))
    to_try = [d for d in ordered if _should_try_domain(d, heads)]
    if not to_try:
        return []

    need_fetch = [d for d in to_try if d not in heads][: max_items + 4]
    if need_fetch:
        heads = {
            **heads,
            **fetch_site_heads(
                need_fetch,
                timeout_s=METADATA_TIMEOUT_S,
                concurrency=METADATA_CONCURRENCY,
            ),
        }

    out: list[DiscoveredCompetitor] = []
    for domain in to_try:
        if len(out) >= max_items:
            break
        head = heads.get(domain)
        if not head or not head.reachable:
            logger.info("竞品发现: 站点不可打开，跳过 %s", domain)
            continue
        out.append(
            DiscoveredCompetitor(
                domain=domain,
                site_name=site_name_from_title(head.title, domain=domain),
            ),
        )

    if len(out) < min_items:
        logger.warning(
            "竞品发现: 可打开竞品仅 %d 个（目标>=%d），可检查搜索质量/预排除规则或调低 COMPETITOR_MIN_SCORE",
            len(out),
            min_items,
        )

    logger.info(
        "竞品发现: 输出 %d 个竞品 %s",
        len(out),
        ", ".join(f"{c['domain']}({c['site_name']})" for c in out),
    )
    return out
