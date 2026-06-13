"""竞品发现诊断日志：输出完整 URL 与筛选原因，便于排查。"""

from __future__ import annotations

import logging

from aperix_geo.services.competitor.filters import should_skip_domain
from aperix_geo.services.competitor.types import SearchPool
from aperix_geo.services.crawl.metadata import PageMetadata
from aperix_geo.services.searxng import SearchHit
from aperix_geo.utils.domains import is_valid_hostname, registrable_domain
from aperix_geo.utils.url import host_resolves, hostname_from_url

logger = logging.getLogger(__name__)


def log_hit_line(
    hit: SearchHit | None,
    *,
    domain: str,
    tag: str,
    extra: str = "",
) -> None:
    url = (hit.url or "").strip() if hit else ""
    title = (hit.title or "")[:100] if hit else ""
    suffix = f" {extra}" if extra else ""
    logger.info(
        "竞品发现: %s domain=%s url=%s title=%r%s",
        tag,
        domain,
        url or "—",
        title,
        suffix,
    )


def log_pool_domains(pool: SearchPool, *, tag: str, domains: list[str]) -> None:
    if not domains:
        return
    logger.info("竞品发现: %s %d 个主域名", tag, len(domains))
    for domain in domains:
        log_hit_line(pool.hit_by_domain.get(domain), domain=domain, tag=tag)


def log_searxng_hit_decisions(
    hits: list[SearchHit],
    *,
    self_domain: str,
    pool_before: set[str],
    added_hosts: list[str],
    max_items: int = 30,
) -> None:
    """逐条记录 SearXNG 命中及入池/跳过原因。"""
    added_set = set(added_hosts)
    for idx, hit in enumerate(hits[:max_items], start=1):
        url = (hit.url or "").strip()
        host = registrable_domain(hostname_from_url(url) or "")
        if not url:
            reason = "跳过:无 URL"
        elif not host or not is_valid_hostname(host):
            reason = "跳过:无效域名"
        elif host == self_domain:
            reason = "跳过:主体自身"
        elif should_skip_domain(host):
            reason = "收录文章(不入域名池)"
        elif host in pool_before:
            reason = "跳过:主域名已在池"
        elif host in added_set:
            reason = "新增入池"
        elif not host_resolves(host):
            reason = "跳过:DNS 不可解析"
        else:
            reason = "跳过:重复 hit"
        logger.info(
            "竞品发现: SearXNG[%d] %s url=%s title=%r",
            idx,
            reason,
            url,
            (hit.title or "")[:80],
        )


def log_enrich_urls(urls: list[str], seo_by_url: dict[str, PageMetadata]) -> None:
    if not urls:
        return
    logger.info("竞品发现: 资讯 enrichment 抓取 %d 条 URL", len(urls))
    for url in urls:
        parsed = seo_by_url.get(url)
        if parsed is None:
            status = "无有效 SEO"
        elif parsed.has_content():
            parts: list[str] = []
            if parsed.title:
                parts.append(f"title={parsed.title[:60]!r}")
            if parsed.body_text.strip():
                parts.append(f"body={len(parsed.body_text.strip())}字")
            status = "ok " + " ".join(parts) if parts else "ok"
        else:
            status = "无有效 SEO"
        logger.info("竞品发现:   enrich url=%s → %s", url, status)


def log_cross_validate_score(
    *,
    domain: str,
    score: float,
    reason: str,
    hit: SearchHit | None,
    reachable: bool | None = None,
) -> None:
    url = (hit.url or "").strip() if hit else ""
    reach = ""
    if reachable is not None:
        reach = " 可打开" if reachable else " 不可打开"
    logger.info(
        "竞品发现: 交叉验算 %s score=%.1f url=%s%s %s",
        domain,
        score,
        url or "—",
        reach,
        reason[:120],
    )
