"""从搜索摘要抽取竞品品牌名（开集抽取 + 归一化）。"""

from __future__ import annotations

import logging
from typing import Any

from aperix_geo.services.brand.keys import configured_brand_keys
from aperix_geo.services.brand.resolve import normalize_brand_key
from aperix_geo.utils.domains import is_valid_hostname, strip_hostname
from aperix_geo.services.competitor.profile import region_label
from aperix_geo.services.competitor.types import NicheProfile, SearchPool
from aperix_geo.services.crawl.metadata import PageMetadata
from aperix_geo.services.providers.prompts import (
    COMPETITOR_SNIPPET_BRAND_EXTRACTION_SYSTEM,
    competitor_snippet_brand_extraction_user_content,
)
from aperix_geo.services.providers import chat_completion
from aperix_geo.services.searxng import SearchHit
from aperix_geo.utils.json import extract_json_object

logger = logging.getLogger(__name__)

_BODY_EXCERPT_CHARS = 1500
_MAX_HITS_IN_PROMPT = 20


def _hit_text_for_llm(hit: SearchHit, page: PageMetadata | None) -> str:
    parts = [hit.title or "", hit.snippet or ""]
    if page is not None:
        prose = page.seo_prose(max_chars=800)
        if prose:
            parts.append(prose)
        body = page.body_text.strip()
        if body:
            parts.append(body[:_BODY_EXCERPT_CHARS])
    return "\n".join(p for p in parts if p.strip())


def format_search_block(
    pool: SearchPool,
    *,
    seo_by_url: dict[str, PageMetadata] | None = None,
) -> str:
    lines: list[str] = []
    seo_map = seo_by_url or {}
    for idx, hit in enumerate(pool.hits[:_MAX_HITS_IN_PROMPT], start=1):
        title = (hit.title or "（无标题）")[:120]
        snippet = (hit.snippet or "（无摘要）")[:220]
        url = (hit.url or "")[:200]
        block = f"{idx}. {title}\n   摘要：{snippet}\n   来源：{url or '—'}"
        page = seo_map.get((hit.url or "").strip())
        if page is not None:
            prose = page.seo_prose(max_chars=800)
            if prose:
                block += f"\n   页面SEO：{prose}"
            body = page.body_text.strip()
            if body:
                block += f"\n   正文摘录：{body[:_BODY_EXCERPT_CHARS]}"
        lines.append(block)
    return "\n".join(lines)


def normalize_snippet_competitor_brands(
    data: dict[str, Any],
    *,
    target_brand: str,
    max_brands: int,
) -> list[str]:
    """Parse LLM brand_names array; filter closed set and domains."""
    raw = data.get("brand_names")
    if not isinstance(raw, list):
        return []

    excluded = configured_brand_keys(own_brand=target_brand)
    out: list[str] = []
    for item in raw:
        label = str(item or "").strip()
        if not label or len(label) > 120:
            continue
        if normalize_brand_key(label) in excluded:
            continue
        if is_valid_hostname(strip_hostname(label)):
            continue
        out.append(label)
        if len(out) >= max_brands:
            break

    return list(dict.fromkeys(out))


def select_brand_names(
    profile: NicheProfile,
    *,
    brand: str,
    pool: SearchPool,
    region: str,
    language: str,
    seo_by_url: dict[str, PageMetadata] | None = None,
) -> list[str]:
    from aperix_geo.services.competitor.defaults import RESULT_MAX

    if not pool.hits:
        logger.warning("竞品品牌抽取：无搜索结果，跳过 LLM")
        return []

    max_brands = RESULT_MAX
    region_label_text = region_label(region)
    messages = [
        {"role": "system", "content": COMPETITOR_SNIPPET_BRAND_EXTRACTION_SYSTEM},
        {
            "role": "user",
            "content": competitor_snippet_brand_extraction_user_content(
                brand=brand,
                profile=profile,
                region_label=region_label_text,
                language=language,
                search_block=format_search_block(pool, seo_by_url=seo_by_url),
                max_brands=max_brands,
            ),
        },
    ]
    text, _, _ = chat_completion(messages, temperature=0.2, json_mode=True)
    brands = normalize_snippet_competitor_brands(
        extract_json_object(text),
        target_brand=brand,
        max_brands=max_brands,
    )
    for name in brands:
        logger.info("竞品发现: 摘要抽取品牌 %r", name)
    return brands
