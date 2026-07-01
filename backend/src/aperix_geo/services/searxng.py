"""SearXNG JSON API 客户端（采样后品牌域名回填等）。"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import httpx

from aperix_geo.config import get_settings
from aperix_geo.utils.http import BROWSER_HEADERS
from aperix_geo.utils.net import host_from

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
    host = host_from(url)
    if not host:
        return False
    if host in _BAIDU_SKIP_NETLOCS:
        return False
    if host.endswith(".baidu.com"):
        return False
    if "baidu.com/link" in url:
        return False
    return True


def _search_searxng(
    query: str,
    *,
    max_results: int,
    base_url: str,
    timeout_s: float = 30.0,
) -> list[SearchHit]:
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
            timeout=timeout_s,
        )
        resp.raise_for_status()
        payload = resp.json()
    except (httpx.HTTPError, ValueError):
        logger.warning("SearXNG: 搜索失败 查询=%r", q, exc_info=True)
        return []

    raw_results = payload.get("results") or []
    raw_count = len(raw_results) if isinstance(raw_results, list) else 0
    if raw_count == 0:
        dead = payload.get("unresponsive_engines") or []
        if dead:
            logger.warning("SearXNG: 原始条数=0 不可用引擎=%s", dead)

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

    logger.debug(
        "SearXNG: 查询=%r 原始条数=%d 可用条数=%d",
        q,
        raw_count,
        len(hits),
    )
    return hits


def search_text(
    query: str,
    *,
    max_results: int | None = None,
    timeout_s: float | None = None,
) -> list[SearchHit]:
    """通用 SearXNG 文本搜索（须配置 SEARXNG_BASE_URL）。"""
    settings = get_settings()
    limit = max(3, min(max_results or 10, 50))
    search_timeout = timeout_s if timeout_s is not None else settings.searxng_timeout_s

    base_url = settings.searxng_base_url.strip()
    if not base_url:
        logger.warning("SearXNG: 未配置 SEARXNG_BASE_URL，跳过搜索 查询=%r", query)
        return []

    return _search_searxng(
        query,
        max_results=limit,
        base_url=base_url,
        timeout_s=search_timeout,
    )
