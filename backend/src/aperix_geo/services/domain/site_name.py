"""Resolve DomainProfile.site_name from the registrable domain homepage (not article pages)."""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from aperix_geo.db.models import DomainProfile
from aperix_geo.services.crawl import fetch_page, page_crawl_settings
from aperix_geo.services.crawl.metadata import SeoProfile, extract_metadata_from_fetch
from aperix_geo.services.crawl.seo import coalesce_site_name
from aperix_geo.services.crawl.settings import seo_fetch_max_chars
from aperix_geo.utils.net import homepage_url_candidates, registrable_from

logger = logging.getLogger(__name__)


def _normalize_domain(domain: str) -> str:
    raw = (domain or "").strip().lower()
    if not raw:
        return ""
    return registrable_from(raw) or raw


def fetch_site_name_from_homepage(domain: str) -> str:
    """Visit ``https://www.{domain}/`` (and apex / http fallbacks); return site brand name."""
    root = _normalize_domain(domain)
    if not root:
        return ""

    urls = homepage_url_candidates(root, prefer_www=True, include_http=True)
    if not urls:
        return ""

    crawl = page_crawl_settings()
    max_chars = seo_fetch_max_chars(crawl)
    for url in urls:
        result = fetch_page(
            url,
            crawl=crawl,
            max_chars=max_chars,
            crawl_fallback=crawl.crawl_fallback,
        )
        if not result.fetch_ok:
            continue
        parsed = extract_metadata_from_fetch(
            result,
            html_parse_limit=max_chars,
            include_body=False,
            seo_profile=SeoProfile.SUBJECT_HOMEPAGE,
        )
        name = coalesce_site_name(
            site_name=str(parsed.site_name or "").strip(),
            publisher=str(parsed.publisher or "").strip(),
            breadcrumbs=list(parsed.breadcrumbs or []),
            title=str(parsed.title or "").strip(),
            domain=root,
        )
        if name:
            logger.info(
                "域名 site_name 首页解析 domain=%s url=%s name=%r",
                root,
                result.final_url or url,
                name,
            )
            return name[:255]
    return ""


def domains_needing_homepage_site_name(db: Session, domains: Iterable[str]) -> list[str]:
    """Domains with empty or headline-like site_name that should be resolved from homepage."""
    keys = sorted({_normalize_domain(d) for d in domains if _normalize_domain(d)})
    if not keys:
        return []
    rows = db.execute(
        select(DomainProfile.domain, DomainProfile.site_name).where(
            DomainProfile.domain.in_(keys),
            DomainProfile.deleted.is_(False),
        )
    ).all()
    existing = {str(domain): str(site_name or "").strip() for domain, site_name in rows}
    out: list[str] = []
    for domain in keys:
        name = existing.get(domain, "")
        if not name or len(name) > 20:
            out.append(domain)
    # profiles not yet created still need resolve
    for domain in keys:
        if domain not in existing and domain not in out:
            out.append(domain)
    return out


def fill_domain_site_names_from_homepage(
    db: Session,
    domains: Iterable[str],
    *,
    concurrency: int | None = None,
) -> dict[str, str]:
    """Fetch homepage site_name for domains missing / headline-like DomainProfile.site_name."""
    from aperix_geo.services.domain.classify import (
        ensure_domain_profiles,
        remember_domain_site_names,
    )

    pending = domains_needing_homepage_site_name(db, domains)
    if not pending:
        return {}

    ensure_domain_profiles(db, pending)
    crawl = page_crawl_settings()
    workers = max(1, min(len(pending), concurrency if concurrency is not None else crawl.concurrency))
    found: dict[str, str] = {}

    def run_one(host: str) -> tuple[str, str]:
        return host, fetch_site_name_from_homepage(host)

    with ThreadPoolExecutor(max_workers=workers) as pool:
        for host, name in pool.map(run_one, pending):
            if name:
                found[host] = name

    if found:
        remember_domain_site_names(db, found)
    return found


def maybe_enqueue_domain_site_name(domains: Iterable[str]) -> None:
    """Enqueue homepage site_name resolve for new domains (coalesced 1h)."""
    keys = sorted({_normalize_domain(d) for d in domains if _normalize_domain(d)})
    if not keys:
        return
    from aperix_geo.utils.cache.redis_kv import redis_set_nx

    to_send: list[str] = []
    for domain in keys:
        if redis_set_nx(f"aperix:domain:site_name:{domain}", ttl_s=3600):
            to_send.append(domain)
    if not to_send:
        return

    from aperix_geo.tasks.domain import resolve_domain_site_names

    resolve_domain_site_names.delay(to_send)
