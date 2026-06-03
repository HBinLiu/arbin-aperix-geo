"""轻量抓取竞品候选站首页 title / meta description。"""

from __future__ import annotations

import asyncio
import logging

import httpx

from aperix_geo.services.competitor.types import SiteHead
from aperix_geo.utils.domains import registrable_domain
from aperix_geo.utils.html import parse_head_from_html
from aperix_geo.utils.http import HTML_FETCH_HEADERS
from aperix_geo.utils.url import homepage_urls

logger = logging.getLogger(__name__)


async def _fetch_one(
    client: httpx.AsyncClient,
    domain: str,
    *,
    timeout_s: float,
) -> SiteHead:
    urls = homepage_urls(domain)
    if not urls:
        return SiteHead(domain=domain, title="", description="", reachable=False)

    for url in urls:
        try:
            resp = await client.get(url, follow_redirects=True, timeout=timeout_s)
            resp.raise_for_status()
            title, description = parse_head_from_html(resp.text[:80_000])
            if title or description:
                return SiteHead(
                    domain=domain,
                    title=title,
                    description=description,
                    reachable=True,
                )
        except httpx.HTTPError:
            continue

    return SiteHead(domain=domain, title="", description="", reachable=False)


async def fetch_site_heads_async(
    domains: list[str],
    *,
    timeout_s: float,
    concurrency: int,
) -> dict[str, SiteHead]:
    unique = dedupe_keys(domains)
    if not unique:
        return {}

    sem = asyncio.Semaphore(max(1, concurrency))
    out: dict[str, SiteHead] = {}

    async with httpx.AsyncClient(headers=HTML_FETCH_HEADERS) as client:

        async def run_one(host: str) -> None:
            async with sem:
                head = await _fetch_one(client, host, timeout_s=timeout_s)
                out[registrable_domain(head.domain)] = head

        await asyncio.gather(*(run_one(h) for h in unique))

    ok = sum(1 for h in out.values() if h.reachable)
    logger.info("竞品发现: 抓取站点元数据 %d 个，可打开 %d", len(out), ok)
    return out


def fetch_site_heads(
    domains: list[str],
    *,
    timeout_s: float = 8.0,
    concurrency: int = 25,
) -> dict[str, SiteHead]:
    return asyncio.run(
        fetch_site_heads_async(
            domains,
            timeout_s=timeout_s,
            concurrency=concurrency,
        ),
    )


def dedupe_keys(domains: list[str]) -> list[str]:
    return list(dict.fromkeys(registrable_domain(d) for d in domains if d.strip()))
