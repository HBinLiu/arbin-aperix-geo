"""竞品发现网页搜索（SearXNG JSON API）。"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import httpx

from aperix_geo.config import get_settings
from aperix_geo.utils.http import BROWSER_HEADERS
from aperix_geo.utils.url import hostname_from_url

logger = logging.getLogger(__name__)
_BAIDU_SKIP_NETLOCS = frozenset(
    {
        "baidu.com",
        "www.baidu.com",
        "baijiahao.baidu.com",
        "tieba.baidu.com",
        "wenku.baidu.com",
        "zhidao.baidu.com",
        "bdstatic.com",
        "bcebos.com",
    },
)

@dataclass(frozen=True)
class SearchHit:
    title: str
    url: str
    snippet: str
    query: str


def _is_usable_result_url(url: str) -> bool:
    if not url.startswith(("http://", "https://")):
        return False
    host = hostname_from_url(url)
    if not host:
        return False
    if host in _BAIDU_SKIP_NETLOCS:
        return False
    if host.endswith(".baidu.com"):
        return False
    if "baidu.com/link" in url:
        return False
    return True


def _search_searxng(query: str, *, max_results: int, base_url: str) -> list[SearchHit]:
    q = query.strip()
    if not q:
        return []

    root = base_url.rstrip("/")
    try:
        resp = httpx.get(
            f"{root}/search",
            params={"q": q, "format": "json", "language": "zh-CN"},
            headers={**BROWSER_HEADERS, "Accept": "application/json"},
            follow_redirects=True,
            timeout=30.0,
        )
        resp.raise_for_status()
        payload = resp.json()
    except (httpx.HTTPError, ValueError):
        logger.warning("竞品发现: 【SearXNG】搜索失败 查询=%r", q, exc_info=True)
        return []

    raw_results = payload.get("results") or []
    raw_count = len(raw_results) if isinstance(raw_results, list) else 0
    if raw_count == 0:
        dead = payload.get("unresponsive_engines") or []
        if dead:
            logger.warning(
                "竞品发现: 【SearXNG】原始条数=0 不可用引擎=%s",
                dead,
            )

    hits: list[SearchHit] = []
    for item in raw_results:
        if not isinstance(item, dict):
            continue
        url = str(item.get("url") or "").strip()
        if not _is_usable_result_url(url):
            continue
        title = str(item.get("title") or "").strip()
        snippet = str(item.get("content") or item.get("snippet") or "").strip()
        hits.append(SearchHit(title=title, url=url, snippet=snippet, query=q))
        if len(hits) >= max_results:
            break

    logger.info(
        "竞品发现: 【SearXNG】查询=%r 原始条数=%d 可用条数=%d",
        q,
        raw_count,
        len(hits),
    )
    return hits


def search_text(query: str, *, max_results: int | None = None) -> list[SearchHit]:
    """竞品发现搜索：仅 SearXNG（须配置 SEARXNG_BASE_URL）。"""
    from aperix_geo.services.competitor.defaults import SEARCH_PAGE_SIZE

    settings = get_settings()
    limit = max_results or SEARCH_PAGE_SIZE
    limit = max(3, min(limit, 50))

    base_url = settings.searxng_base_url.strip()
    if not base_url:
        logger.warning("竞品发现: 未配置 SEARXNG_BASE_URL，跳过搜索 查询=%r", query)
        return []

    return _search_searxng(query, max_results=limit, base_url=base_url)
