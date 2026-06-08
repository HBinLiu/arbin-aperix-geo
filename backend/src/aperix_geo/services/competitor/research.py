"""主体调研：站内多页摘录 + 品牌公开信息搜索。"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Any
from urllib.parse import urljoin, urlparse

from aperix_geo.services.crawl import PageFetchResult, fetch_page, page_crawl_settings
from aperix_geo.services.web_search import SearchHit, search_text
from aperix_geo.utils.domains import registrable_domain
from aperix_geo.utils.html import html_to_text, parse_head_from_html
from aperix_geo.utils.url import homepage_urls

logger = logging.getLogger(__name__)

_PROFILE_EXTRA_PATHS: tuple[tuple[str, str], ...] = (
    ("about", "/about"),
    ("about", "/about-us"),
    ("about", "/aboutus"),
    ("about", "/company"),
    ("about", "/introduction"),
    ("products", "/products"),
    ("products", "/solutions"),
    ("products", "/services"),
)

_MAX_EXTRA_PAGES = 3
_EXTRA_PAGE_EXCERPT_CHARS = 2500
_EXTRA_PAGE_FETCH_CHARS = 120_000
_REGION_SEARCH_LABELS = {"CN": "中国", "HK": "香港", "TW": "台湾"}


def _page_base_url(homepage_url: str, domain: str) -> str:
    if homepage_url.strip():
        parsed = urlparse(homepage_url)
        if parsed.scheme and parsed.netloc:
            return f"{parsed.scheme}://{parsed.netloc}"
    root = registrable_domain(domain)
    candidates = homepage_urls(root) if root else []
    if candidates:
        parsed = urlparse(candidates[0])
        return f"{parsed.scheme}://{parsed.netloc}"
    return f"https://{root or domain}"


def _excerpt_from_fetch(result: PageFetchResult) -> str | None:
    if not result.fetch_ok:
        return None

    title = ""
    description = ""
    if result.html:
        title, description = parse_head_from_html(result.html[:_EXTRA_PAGE_FETCH_CHARS])

    if result.markdown.strip():
        body = result.markdown.strip()[:_EXTRA_PAGE_EXCERPT_CHARS]
    elif result.html:
        body = html_to_text(result.html, limit=_EXTRA_PAGE_EXCERPT_CHARS)
    else:
        body = ""

    parts: list[str] = []
    if title:
        parts.append(f"title: {title}")
    if description:
        parts.append(f"description: {description}")
    if body:
        parts.append(body)
    text = "\n".join(parts).strip()
    return text if len(text) >= 80 else None


def fetch_site_extra_pages(
    domain: str,
    *,
    homepage_url: str = "",
    max_pages: int = _MAX_EXTRA_PAGES,
) -> dict[str, str]:
    crawl = page_crawl_settings()
    base = _page_base_url(homepage_url, domain)
    seen_paths: set[str] = set()
    pending: list[tuple[str, str]] = []
    max_chars = min(crawl.max_chars, _EXTRA_PAGE_FETCH_CHARS)

    for label, path in _PROFILE_EXTRA_PATHS:
        if len(pending) >= max_pages:
            break
        norm = path.rstrip("/").lower()
        if norm in seen_paths:
            continue
        seen_paths.add(norm)
        pending.append((label, path))

    if not pending:
        return {}

    workers = min(len(pending), max(1, crawl.concurrency))

    def _one(item: tuple[str, str]) -> tuple[str, str, str] | None:
        label, path = item
        url = urljoin(base.rstrip("/") + "/", path.lstrip("/"))
        result = fetch_page(url, crawl=crawl, max_chars=max_chars)
        excerpt = _excerpt_from_fetch(result)
        if not excerpt:
            return None
        return label, path, excerpt

    out: dict[str, str] = {}
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for row in pool.map(_one, pending):
            if row is None or len(out) >= max_pages:
                continue
            label, path, excerpt = row
            key = label if label not in out else f"{label}_{path.strip('/')}"
            out[key] = excerpt
            logger.info("主体调研: 补充页 %s path=%s chars=%d", domain, path, len(excerpt))

    return out


def fetch_brand_research_hits(brand: str, *, region: str, max_results: int = 8) -> list[SearchHit]:
    """品牌模式：SearXNG 检索公开信息摘要。"""
    brand = brand.strip()
    if not brand:
        return []
    region_hint = _REGION_SEARCH_LABELS.get(region, region)
    query = f"{brand} {region_hint} 公司 业务 产品"
    return search_text(query, max_results=max_results)


def format_search_hits_for_llm(hits: list[SearchHit], *, max_items: int = 8) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for hit in hits[:max_items]:
        rows.append(
            {
                "title": hit.title[:300],
                "url": hit.url[:500],
                "snippet": hit.snippet[:600],
            },
        )
    return rows


def research_payload_for_domain(
    *,
    domain: str,
    site_metadata: dict[str, str],
    site_markdown: str,
    extra_pages: dict[str, str] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "title": (site_metadata.get("title") or "").strip(),
        "description": (site_metadata.get("description") or "").strip(),
        "h1_h2": (site_metadata.get("h1_h2") or "").strip(),
    }
    if site_markdown.strip():
        payload["homepage_excerpt"] = site_markdown.strip()[:6000]
    if extra_pages:
        payload["extra_pages"] = {k: v[:3000] for k, v in extra_pages.items()}
    if not any(str(v).strip() for v in payload.values() if isinstance(v, str)):
        if not extra_pages:
            payload["domain_hint"] = domain
    return payload
