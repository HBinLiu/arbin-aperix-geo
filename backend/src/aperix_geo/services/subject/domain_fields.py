"""Subject / 竞品域名与 website_url 归一。"""

from __future__ import annotations

from aperix_geo.db.models import SubjectType
from aperix_geo.schemas.url_fields import validate_optional_http_url
from aperix_geo.utils.net import (
    coalesce_explicit_http_url,
    registrable_from,
    resolve_website,
    website_fallback,
)


def _optional_stored_url(raw: str) -> str:
    """存储层 website_url（可含裸 host/path，不触发网络探测）。"""
    try:
        return validate_optional_http_url(raw.strip())
    except ValueError:
        return ""


def prepare_domain_and_website_url(
    raw_domain: str,
    raw_website_url: str = "",
    *,
    probe: bool = True,
) -> tuple[str, str]:
    """归一为 (registrable_domain, website_url)。"""
    domain = registrable_from(raw_domain or raw_website_url)
    if not domain:
        return "", ""

    fetch_url = coalesce_explicit_http_url(raw_website_url)
    if fetch_url:
        return domain, fetch_url

    stored = _optional_stored_url(raw_website_url)
    if stored:
        return domain, stored

    if probe:
        _, website_url = resolve_website(domain, probe=True)
        return domain, website_url
    return domain, website_fallback(domain)


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

    fetch_url = coalesce_explicit_http_url(raw_website_url)
    if fetch_url:
        return "", fetch_url

    stored = _optional_stored_url(raw_website_url)
    if stored:
        return "", stored

    if raw_domain.strip():
        domain = registrable_from(raw_domain)
        if domain:
            return "", website_fallback(domain)
    return "", ""
