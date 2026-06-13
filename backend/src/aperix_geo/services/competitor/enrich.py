"""竞品发现阶段：LLM 生成 brand（公司/品牌名）与 summary（竞品介绍）。"""

from __future__ import annotations

import json
import logging
from typing import Any

from aperix_geo.services.competitor.types import DiscoveredCompetitor, NicheProfile, SiteHead
from aperix_geo.services.providers.prompts import COMPETITOR_DISCOVER_ENRICH_SYSTEM
from aperix_geo.services.providers import chat_completion
from aperix_geo.utils.domains import ensure_brand
from aperix_geo.utils.json import extract_json_object

logger = logging.getLogger(__name__)


def enrich_discovered_competitors(
    competitors: list[DiscoveredCompetitor],
    *,
    profile: NicheProfile,
    subject_type: str,
    heads: dict[str, SiteHead] | None = None,
    region_label: str = "",
    language_label: str = "",
) -> list[DiscoveredCompetitor]:
    """为已发现的竞品补充 brand 与 summary；LLM 失败时保留/回退 title 推导的 brand。"""
    if not competitors:
        return []

    heads = heads or {}
    seeds: list[dict[str, Any]] = []
    for item in competitors:
        domain = str(item.get("domain") or "").strip()
        head = heads.get(domain)
        seed_brand = str(item.get("brand") or "").strip()
        if not seed_brand and domain:
            seed_brand = ensure_brand(None, domain=domain)
        seeds.append(
            {
                "domain": domain,
                "brand_hint": seed_brand,
                "title": (head.title if head else "")[:300],
                "description": (head.description if head else "")[:500],
                "seo": (head.seo if head else "")[:500],
                "summary_hint": str(item.get("summary") or "").strip(),
            }
        )

    from aperix_geo.services.setup.llm.payloads import build_competitor_enrich_payload

    payload = build_competitor_enrich_payload(
        profile=profile,
        subject_type=subject_type,
        seeds=seeds,
        region_label_text=region_label,
        language_label_text=language_label,
    )

    try:
        text, _, latency_ms = chat_completion(
            [
                {"role": "system", "content": COMPETITOR_DISCOVER_ENRICH_SYSTEM},
                {"role": "user", "content": json.dumps(payload, ensure_ascii=False, indent=2)},
            ],
            temperature=0.2,
            json_mode=True,
        )
        raw_items = extract_json_object(text).get("competitors")
        if not isinstance(raw_items, list):
            raise ValueError("invalid competitors array")
        by_key: dict[str, dict[str, str]] = {}
        for row in raw_items:
            if not isinstance(row, dict):
                continue
            domain = str(row.get("domain") or "").strip()
            brand = str(row.get("brand") or "").strip()[:255]
            summary = str(row.get("summary") or "").strip()
            key = domain or brand.casefold()
            if key and brand:
                by_key[key] = {"brand": brand, "summary": summary}

        out: list[DiscoveredCompetitor] = []
        for seed, item in zip(seeds, competitors, strict=True):
            domain = str(item.get("domain") or "").strip()
            key = domain or str(seed.get("brand_hint") or "").casefold()
            enriched = by_key.get(key) or by_key.get(domain) or {}
            brand = ensure_brand(enriched.get("brand") or seed.get("brand_hint"), domain=domain)
            summary = enriched.get("summary") or str(item.get("summary") or "").strip()
            out.append(
                DiscoveredCompetitor(
                    domain=domain,
                    website_url=str(item.get("website_url") or "").strip(),
                    brand=brand[:255],
                    summary=summary,
                )
            )
        logger.info("竞品 enrich: %d 条 (%dms)", len(out), latency_ms)
        return out
    except Exception:
        logger.warning("竞品 enrich 失败，使用主域名回退 brand", exc_info=True)
        return [
            DiscoveredCompetitor(
                domain=str(item.get("domain") or "").strip(),
                website_url=str(item.get("website_url") or "").strip(),
                brand=ensure_brand(item.get("brand") or seed.get("brand_hint"), domain=str(item.get("domain") or ""))[:255],
                summary=str(item.get("summary") or "").strip(),
            )
            for item, seed in zip(competitors, seeds, strict=True)
        ]
