"""Subject / 竞品域名与 website_url 归一。"""

from __future__ import annotations

from aperix_geo.db.models import SubjectType
from aperix_geo.schemas.url_fields import validate_optional_http_url
from aperix_geo.utils.net import registrable_from, resolve_website


def prepare_domain_and_website_url(
    raw_domain: str,
    raw_website_url: str = "",
    *,
    probe: bool = True,
) -> tuple[str, str]:
    """归一为 (registrable_domain, website_url)。用户输入原样保留（http(s) 或裸域名/路径）。"""
    domain = registrable_from(raw_domain or raw_website_url)
    if not domain:
        return "", ""

    user_url = raw_website_url.strip()
    if user_url:
        try:
            validated = validate_optional_http_url(user_url)
        except ValueError:
            validated = ""
        if validated:
            return domain, validated

    _, website_url = resolve_website(domain, probe=probe)
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

    try:
        website_url = validate_optional_http_url(raw_website_url.strip())
    except ValueError:
        website_url = ""
    if website_url:
        return "", website_url
    if raw_domain.strip():
        domain = registrable_from(raw_domain)
        if domain:
            _, website_url = resolve_website(domain, probe=probe)
            return "", website_url
    return "", ""
