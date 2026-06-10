"""Favicon pre-warm helpers."""

from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from aperix_geo.config import get_settings
from aperix_geo.db.models import CitationUrl, LLMResponse
from aperix_geo.services.favicon._domain import normalize_favicon_domain
from aperix_geo.services.favicon._resolve import resolve_favicon_coalesced
from aperix_geo.services.favicon._storage import (
    cache_get,
    negative_cache_hit,
    static_favicon_path,
)
from aperix_geo.utils.domains import is_valid_hostname
from aperix_geo.utils.url import hostname_from_url

logger = logging.getLogger(__name__)


def citation_hosts_for_job(db: Session, job_id: UUID) -> list[str]:
    """Unique normalized hosts from citation URLs in a sampling job."""
    urls = db.execute(
        select(CitationUrl.url)
        .join(LLMResponse, CitationUrl.response_id == LLMResponse.id)
        .where(LLMResponse.sampling_job_id == job_id),
    ).scalars().all()

    hosts: list[str] = []
    seen: set[str] = set()
    for url in urls:
        raw = (url or "").strip()
        if not raw:
            continue
        host = normalize_favicon_domain(hostname_from_url(raw) or raw)
        if not host or not is_valid_hostname(host) or host in seen:
            continue
        seen.add(host)
        hosts.append(host)
    return hosts


def _unique_valid_hosts(hosts: list[str]) -> list[str]:
    unique: list[str] = []
    seen: set[str] = set()
    for raw in hosts:
        host = normalize_favicon_domain(raw)
        if not host or not is_valid_hostname(host) or host in seen:
            continue
        seen.add(host)
        unique.append(host)
    return unique


def warm_favicon_hosts(
    hosts: list[str],
    *,
    concurrency: int | None = None,
    job_id: str | None = None,
) -> dict[str, int]:
    """Resolve favicons for hosts not already cached on disk or in memory."""
    stats = {"total": 0, "skipped": 0, "resolved": 0, "miss": 0}
    unique_hosts = _unique_valid_hosts(hosts)
    stats["total"] = len(unique_hosts)
    if not unique_hosts:
        return stats

    label = job_id or "-"
    settings = get_settings()
    workers = min(len(unique_hosts), max(1, concurrency or settings.favicon_warm_concurrency))

    pending: list[str] = []
    for host in unique_hosts:
        if negative_cache_hit(host) or cache_get(host) or static_favicon_path(host):
            stats["skipped"] += 1
        else:
            pending.append(host)

    if not pending:
        logger.info(
            "favicon 预热跳过 job=%s total=%d skipped=%d（均已缓存）",
            label,
            stats["total"],
            stats["skipped"],
        )
        return stats

    logger.info(
        "favicon 预热开始 job=%s total=%d pending=%d concurrency=%d",
        label,
        stats["total"],
        len(pending),
        workers,
    )
    started = time.monotonic()
    done = 0
    pending_total = len(pending)
    log_step = max(1, pending_total // 10)

    def _resolve_one(host: str) -> str:
        return "resolved" if resolve_favicon_coalesced(host) else "miss"

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(_resolve_one, host) for host in pending]
        for fut in as_completed(futures):
            stats[fut.result()] += 1
            done += 1
            if done % log_step == 0 or done == pending_total:
                logger.info(
                    "favicon 预热进度 job=%s %d/%d resolved=%d miss=%d",
                    label,
                    done,
                    pending_total,
                    stats["resolved"],
                    stats["miss"],
                )

    elapsed = time.monotonic() - started
    logger.info(
        "favicon 预热完成 job=%s total=%d skipped=%d resolved=%d miss=%d elapsed=%.1fs",
        label,
        stats["total"],
        stats["skipped"],
        stats["resolved"],
        stats["miss"],
        elapsed,
    )
    return stats
