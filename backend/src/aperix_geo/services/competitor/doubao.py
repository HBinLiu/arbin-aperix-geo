"""豆包联网竞品发现。"""

from __future__ import annotations

from aperix_geo.config import get_settings
from aperix_geo.services.competitor.parse import parse_doubao_competitors_payload
from aperix_geo.services.competitor.profile import language_label, region_label
from aperix_geo.services.competitor.types import (
    CandidateMeta,
    CandidatePool,
    DiscoveredCompetitor,
    NicheProfile,
    SubjectType,
)
from aperix_geo.services.providers.doubao import doubao_responses_chat
from aperix_geo.services.providers.errors import DoubaoProviderError
from aperix_geo.services.providers.prompts import (
    COMPETITOR_DOUBAO_DISCOVER_BRAND_SYSTEM,
    COMPETITOR_DOUBAO_DISCOVER_DOMAIN_SYSTEM,
    competitor_doubao_discover_brand_user_content,
    competitor_doubao_discover_domain_user_content,
)
from aperix_geo.utils.net import registrable_from


def pool_from_discovered_competitors(competitors: list[DiscoveredCompetitor]) -> CandidatePool:
    """将 discover 候选转为交叉验算候选池。"""
    domains: list[str] = []
    by_domain: dict[str, CandidateMeta] = {}
    for item in competitors:
        domain = registrable_from(str(item.get("domain") or ""))
        if not domain or domain in by_domain:
            continue
        url = str(item.get("website_url") or "").strip() or f"https://{domain}/"
        by_domain[domain] = CandidateMeta(
            domain=domain,
            brand=str(item.get("brand") or "").strip(),
            website_url=url,
        )
        domains.append(domain)
    return CandidatePool(domains=domains, by_domain=by_domain)


def discover_competitors_via_doubao(
    profile: NicheProfile,
    *,
    subject_type: SubjectType,
    target: str,
    website_url: str = "",
    region: str = "CN",
    language: str = "zh-CN",
) -> list[DiscoveredCompetitor]:
    """调用豆包 Responses API（联网）抽取竞品列表。"""
    settings = get_settings()
    if not settings.doubao_api_key.strip():
        raise DoubaoProviderError("Doubao API key is not configured")

    region_label_value = region_label(region)
    language_label_value = language_label(language)
    if subject_type == "brand":
        user_content = competitor_doubao_discover_brand_user_content(
            target=target,
            profile=profile,
            region=region_label_value,
            language=language_label_value,
        )
        system_prompt = COMPETITOR_DOUBAO_DISCOVER_BRAND_SYSTEM
        self_domain = ""
        self_brand = target.strip()
    else:
        user_content = competitor_doubao_discover_domain_user_content(
            target=target,
            website_url=website_url,
            profile=profile,
            region=region_label_value,
            language=language_label_value,
        )
        system_prompt = COMPETITOR_DOUBAO_DISCOVER_DOMAIN_SYSTEM
        self_domain = registrable_from(target)
        self_brand = ""

    result = doubao_responses_chat(
        [{"role": "user", "content": user_content}],
        api_key=settings.doubao_api_key,
        base_url=settings.doubao_base_url,
        model=settings.doubao_model,
        web_search=settings.doubao_web_search_enabled,
        timeout_s=settings.doubao_responses_timeout_s,
        system_prompt=system_prompt,
    )

    return parse_doubao_competitors_payload(
        result.text,
        mode=subject_type,
        self_domain=self_domain,
        self_brand=self_brand,
    )
