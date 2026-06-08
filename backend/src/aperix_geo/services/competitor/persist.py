"""竞品列表持久化（设置向导 finalize 与 CRUD 共用）。"""

from __future__ import annotations

from aperix_geo.db.models import Competitor, Subject
from aperix_geo.schemas.catalog import CompetitorItem
from aperix_geo.services.subject.domain_fields import prepare_domain_and_website_url
from aperix_geo.utils.domains import ensure_brand


def apply_competitors(
    subject: Subject,
    *,
    competitors: list[CompetitorItem],
) -> None:
    seen_domains: set[str] = set()
    seen_brands: set[str] = set()
    for item in competitors:
        summary = (item.summary or "").strip()
        domain_raw = (item.domain or "").strip()
        if domain_raw:
            domain, website_url = prepare_domain_and_website_url(domain_raw, item.website_url)
            if not domain or len(domain) < 3 or domain in seen_domains:
                continue
            seen_domains.add(domain)
            brand = ensure_brand(item.brand, domain=domain)
            subject.competitors.append(
                Competitor(
                    domain=domain,
                    website_url=website_url,
                    brand=brand,
                    summary=summary,
                )
            )
            continue

        brand = ensure_brand(item.brand)
        if not brand:
            continue
        key = brand.casefold()
        if key in seen_brands:
            continue
        seen_brands.add(key)
        subject.competitors.append(
            Competitor(domain="", website_url="", brand=brand, summary=summary)
        )
