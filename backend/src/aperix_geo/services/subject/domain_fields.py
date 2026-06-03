"""Subject / 竞品域名与 website_url 归一。"""

from __future__ import annotations

from aperix_geo.db.models import SubjectType
from aperix_geo.utils.domains import registrable_domain
from aperix_geo.utils.url import resolve_website_url, root_website_url


def prepare_domain_and_website_url(
    raw_domain: str,
    raw_website_url: str = "",
    *,
    probe: bool = True,
) -> tuple[str, str]:
    """归一为 (registrable_domain, website_url)。"""
    domain = registrable_domain(raw_domain or raw_website_url)
    if not domain:
        return "", ""

    website_url = root_website_url(raw_website_url.strip()) if raw_website_url.strip() else ""
    if website_url:
        return domain, website_url

    _, website_url = resolve_website_url(domain, probe=probe)
    return domain, website_url


def apply_subject_domain_fields(
    *,
    subject_type: SubjectType,
    raw_domain: str,
    raw_website_url: str = "",
    probe: bool = True,
) -> tuple[str, str]:
    """
    domain 主体：domain 存 eTLD+1，website_url 存完整根链接。
    brand 主体：domain 为空；website_url 可选（官网，用于引用率）。
    """
    if subject_type == SubjectType.domain:
        return prepare_domain_and_website_url(raw_domain, raw_website_url, probe=probe)

    website_url = root_website_url(raw_website_url.strip()) if raw_website_url.strip() else ""
    if website_url:
        return "", website_url
    if raw_domain.strip():
        domain = registrable_domain(raw_domain)
        if domain:
            _, website_url = resolve_website_url(domain, probe=probe)
            return "", website_url
    return "", ""
