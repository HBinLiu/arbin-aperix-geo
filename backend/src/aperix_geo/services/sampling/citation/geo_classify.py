"""Schema + rule-based citation page / domain GEO classification."""

from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urlparse

from aperix_geo.services.sampling.citation.page import CitationPageMeta, page_mentions_any_term
from aperix_geo.utils.domains import registrable_domain
from aperix_geo.utils.url import host_matches_root, hostname_from_url

URL_TYPE_OTHER = "其它类型"
DOMAIN_TYPE_OTHER = "其它类型"
DOMAIN_TYPE_ENTERPRISE = "企业/品牌官网"

_COMMUNITY_REGISTRABLE = frozenset(
    {
        "zhihu.com",
        "reddit.com",
        "stackoverflow.com",
        "stackexchange.com",
        "v2ex.com",
        "douban.com",
        "tieba.baidu.com",
        "xiaohongshu.com",
    },
)
_CODE_REGISTRABLE = frozenset(
    {
        "github.com",
        "gitlab.com",
        "gitee.com",
        "huggingface.co",
        "bitbucket.org",
    },
)
_WIKI_REGISTRABLE = frozenset(
    {
        "wikipedia.org",
        "wikimedia.org",
        "baike.baidu.com",
        "wikiwand.com",
    },
)
_MARKETPLACE_REGISTRABLE = frozenset(
    {
        "g2.com",
        "capterra.com",
        "producthunt.com",
        "apps.apple.com",
        "play.google.com",
    },
)

_SCHEMA_URL_TYPE: dict[str, str] = {
    "product": "产品详情",
    "softwareapplication": "产品详情",
    "webapplication": "产品详情",
    "mobileapplication": "产品详情",
    "newsarticle": "动态新闻",
    "reportagenewsarticle": "动态新闻",
    "article": "普通文章",
    "blogposting": "普通文章",
    "techarticle": "普通文章",
    "scholarlyarticle": "行业报告",
    "report": "行业报告",
    "howto": "实操指南",
    "itemlist": "盘点清单",
    "faqpage": "普通文章",
    "qapage": "社区讨论",
    "discussionforumposting": "社区讨论",
    "socialmediaposting": "社区讨论",
}

_OG_URL_TYPE: dict[str, str] = {
    "product": "产品详情",
    "article": "普通文章",
    "website": "品牌官网",
}

_PRODUCT_PATH_RE = re.compile(
    r"/(?:pricing|price|plans|product|products|features|buy|purchase)(?:/|$)",
    re.IGNORECASE,
)
_HOME_PATH_RE = re.compile(r"^/(?:index\.html?)?$", re.IGNORECASE)


@dataclass(frozen=True)
class GeoClassification:
    url_type: str = ""
    url_reason: str = ""
    domain_type: str = ""
    domain_reason: str = ""

    @property
    def url_resolved(self) -> bool:
        return bool(self.url_type)

    @property
    def domain_resolved(self) -> bool:
        return bool(self.domain_type)

    @property
    def complete(self) -> bool:
        return self.url_resolved and self.domain_resolved

    def needs_llm(self) -> bool:
        return not self.complete


def _normalized_schema_types(page: CitationPageMeta) -> list[str]:
    return [str(t).strip().lower() for t in page.schema_types if str(t).strip()]


def _host_registrable(page: CitationPageMeta) -> str:
    host = hostname_from_url(page.url) or page.domain
    return (registrable_domain(host) or host or "").lower()


def _path_of(url: str) -> str:
    try:
        return urlparse(url.strip()).path or "/"
    except ValueError:
        return "/"


def _gov_or_edu_domain(host: str) -> str | None:
    lower = host.lower()
    if lower.endswith(".gov.cn") or lower.endswith(".gov"):
        return "政府/公共机构"
    if lower.endswith(".edu.cn") or lower.endswith(".edu"):
        return "教育/科研机构"
    if ".ac.cn" in lower or lower.endswith(".ac.uk"):
        return "教育/科研机构"
    return None


def classify_domain_type(
    page: CitationPageMeta,
    *,
    enterprise_roots: frozenset[str] | set[str],
) -> tuple[str, str]:
    if page.http_status is not None and page.http_status != 200:
        return DOMAIN_TYPE_OTHER, "http_status 异常"

    host = hostname_from_url(page.url) or page.domain
    if not host:
        return "", ""

    registrable = _host_registrable(page)
    gov_edu = _gov_or_edu_domain(host)
    if gov_edu:
        return gov_edu, f"域名后缀 {host}"

    if registrable in _CODE_REGISTRABLE:
        return "代码/开源平台", f"已知平台 {registrable}"
    if registrable in _COMMUNITY_REGISTRABLE:
        return "社区/社交平台", f"已知平台 {registrable}"
    if registrable in _WIKI_REGISTRABLE:
        return "参考资料/百科", f"已知平台 {registrable}"
    if registrable in _MARKETPLACE_REGISTRABLE:
        return "软件市场/垂直目录", f"已知平台 {registrable}"

    for root in enterprise_roots:
        if host_matches_root(host, root):
            return DOMAIN_TYPE_ENTERPRISE, f"监测域名 {root}"

    return "", ""


def _schema_url_type(schema_types: list[str]) -> tuple[str, str]:
    for raw in schema_types:
        key = raw.replace(" ", "").lower()
        hit = _SCHEMA_URL_TYPE.get(key)
        if hit:
            return hit, f"schema.org {raw}"
    return "", ""


def _og_url_type(content_type: str) -> tuple[str, str]:
    key = (content_type or "").strip().lower()
    if not key:
        return "", ""
    hit = _OG_URL_TYPE.get(key)
    if hit:
        return hit, f"og:type {content_type}"
    return "", ""


def _rule_url_type(
    page: CitationPageMeta,
    *,
    enterprise_roots: frozenset[str] | set[str],
    page_brand_scope: list[str],
) -> tuple[str, str]:
    if page.http_status is not None and page.http_status != 200:
        return URL_TYPE_OTHER, "http_status 异常"
    if not page.fetch_ok or not (page.text_snippet or "").strip():
        return URL_TYPE_OTHER, "正文不可用"

    host = hostname_from_url(page.url) or page.domain
    path = _path_of(page.url)
    registrable = _host_registrable(page)

    if registrable in _COMMUNITY_REGISTRABLE:
        return "社区讨论", f"社区域名 {registrable}"

    if page.has_code_block:
        return "实操指南", "has_code_block"

    if page.has_table and page_brand_scope:
        mentioned = sum(
            1
            for brand in page_brand_scope
            if page_mentions_any_term(page.text_snippet, (brand,))
        )
        if mentioned >= 2:
            return "对比评测", "has_table 且正文涉及多品牌"

    if _PRODUCT_PATH_RE.search(path):
        return "产品详情", f"URL 路径 {path}"

    for root in enterprise_roots:
        if host and host_matches_root(host, root) and _HOME_PATH_RE.match(path):
            return "品牌官网", f"监测域名首页 {root}"

    if len((page.text_snippet or "").strip()) >= 3500:
        return "行业报告", "正文篇幅较长"

    return "", ""


def classify_url_type(
    page: CitationPageMeta,
    *,
    enterprise_roots: frozenset[str] | set[str],
    page_brand_scope: list[str],
) -> tuple[str, str]:
    schema_types = _normalized_schema_types(page)
    hit, reason = _schema_url_type(schema_types)
    if hit:
        if hit == "品牌官网":
            path = _path_of(page.url)
            host = hostname_from_url(page.url) or page.domain
            for root in enterprise_roots:
                if host and host_matches_root(host, root) and _HOME_PATH_RE.match(path):
                    return hit, reason
        else:
            return hit, reason

    hit, reason = _og_url_type(page.content_type)
    if hit:
        if hit == "品牌官网":
            path = _path_of(page.url)
            host = hostname_from_url(page.url) or page.domain
            for root in enterprise_roots:
                if host and host_matches_root(host, root) and _HOME_PATH_RE.match(path):
                    return hit, reason
        elif hit != "品牌官网":
            return hit, reason

    return _rule_url_type(
        page,
        enterprise_roots=enterprise_roots,
        page_brand_scope=page_brand_scope,
    )


def classify_citation_page_geo(
    page: CitationPageMeta,
    *,
    enterprise_roots: frozenset[str] | set[str],
    page_brand_scope: list[str] | None = None,
) -> GeoClassification:
    """Schema-first, then rules. Empty fields mean LLM fallback is needed."""
    scope = page_brand_scope or []
    domain_type, domain_reason = classify_domain_type(page, enterprise_roots=enterprise_roots)
    url_type, url_reason = classify_url_type(
        page,
        enterprise_roots=enterprise_roots,
        page_brand_scope=scope,
    )
    return GeoClassification(
        url_type=url_type,
        url_reason=url_reason,
        domain_type=domain_type,
        domain_reason=domain_reason,
    )


def geo_classification_to_analysis(
    classification: GeoClassification,
    *,
    analysis_source: str = "rule",
) -> dict[str, object]:
    url_type = classification.url_type or URL_TYPE_OTHER
    domain_type = classification.domain_type or DOMAIN_TYPE_OTHER
    url_reason = classification.url_reason or ("规则未匹配" if not classification.url_resolved else "")
    domain_reason = classification.domain_reason or (
        "规则未匹配" if not classification.domain_resolved else ""
    )
    return {
        "url_classification": {"type": url_type, "reason": url_reason},
        "domain_classification": {"type": domain_type, "reason": domain_reason},
        "page_mentioned_brands": [],
        "analysis_source": analysis_source,
    }


def merge_geo_analysis(
    rule: GeoClassification,
    llm: dict[str, object],
    *,
    analysis_source: str = "hybrid",
) -> dict[str, object]:
    """Prefer schema/rule fields; fill gaps from LLM."""
    url_cls = llm.get("url_classification") if isinstance(llm.get("url_classification"), dict) else {}
    domain_cls = (
        llm.get("domain_classification") if isinstance(llm.get("domain_classification"), dict) else {}
    )
    url_type = rule.url_type or str(url_cls.get("type") or "").strip() or URL_TYPE_OTHER
    domain_type = rule.domain_type or str(domain_cls.get("type") or "").strip() or DOMAIN_TYPE_OTHER
    url_reason = rule.url_reason or str(url_cls.get("reason") or "").strip() or "规则未匹配"
    domain_reason = rule.domain_reason or str(domain_cls.get("reason") or "").strip() or "规则未匹配"

    if rule.complete:
        source = "rule"
    elif rule.url_resolved or rule.domain_resolved:
        source = analysis_source
    else:
        source = str(llm.get("analysis_source") or "llm")

    return {
        "url_classification": {"type": url_type, "reason": url_reason},
        "domain_classification": {"type": domain_type, "reason": domain_reason},
        "page_mentioned_brands": [],
        "analysis_source": source,
    }
