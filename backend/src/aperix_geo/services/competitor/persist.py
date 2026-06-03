"""竞品列表持久化（设置向导 finalize 与 CRUD 共用）。"""

from __future__ import annotations

from aperix_geo.db.models import CompetitorBrand, CompetitorDomain, Subject
from aperix_geo.services.subject.domain_fields import prepare_domain_and_website_url
from aperix_geo.schemas.catalog import CompetitorDomainItem
from aperix_geo.utils.domains import site_name_from_title


def apply_competitors(
    subject: Subject,
    *,
    competitors: list[CompetitorDomainItem],
    brand_names: list[str],
) -> None:
    seen_domains: set[str] = set()
    for item in competitors:
        domain, website_url = prepare_domain_and_website_url(item.domain, item.website_url)
        if not domain or len(domain) < 3 or domain in seen_domains:
            continue
        seen_domains.add(domain)
        site_name = (item.site_name or "").strip()[:255]
        if not site_name:
            site_name = site_name_from_title("", domain=domain)
        subject.competitor_domains.append(
            CompetitorDomain(domain=domain, website_url=website_url, site_name=site_name)
        )

    for name in brand_names:
        name = name.strip()
        if name:
            subject.competitor_brands.append(CompetitorBrand(name=name))
