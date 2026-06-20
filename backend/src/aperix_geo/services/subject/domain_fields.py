"""Subject / 竞品域名与 website_url 归一。"""

from __future__ import annotations

from aperix_geo.db.models import SubjectType
from aperix_geo.utils.domains import registrable_domain
from aperix_geo.utils.url import normalize_user_website_input, resolve_website_url


def prepare_domain_and_website_url(
    raw_domain: str,
    raw_website_url: str = "",
    *,
    probe: bool = True,
) -> tuple[str, str]:
    """归一为 (registrable_domain, website_url)。用户显式提供的 URL 原样保留（仅补全 scheme）。"""
    domain = registrable_domain(raw_domain or raw_website_url)
    if not domain:
        return "", ""

    user_url = normalize_user_website_input(raw_website_url.strip())
    if user_url:
        return domain, user_url

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
    domain 主体：domain 存 eTLD+1，website_url 存用户输入的完整链接（含子域/路径）。
    brand 主体：domain 为空；website_url 可选（官网，用于引用率）。
    """
    if subject_type == SubjectType.domain:
        return prepare_domain_and_website_url(raw_domain, raw_website_url, probe=probe)

    website_url = normalize_user_website_input(raw_website_url.strip())
    if website_url:
        return "", website_url
    if raw_domain.strip():
        domain = registrable_domain(raw_domain)
        if domain:
            _, website_url = resolve_website_url(domain, probe=probe)
            return "", website_url
    return "", ""
