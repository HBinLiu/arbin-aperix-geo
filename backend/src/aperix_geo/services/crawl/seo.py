"""SEO / GEO optimized metadata extraction from HTML head, JSON-LD, and Microdata.

Scene profiles (``SeoProfile``) control which extracted fields each consumer uses.
Parsing always collects all supported tags; ``apply_seo_profile`` filters at use time.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import OrderedDict
from dataclasses import dataclass, replace
from enum import Enum
from typing import Any
from urllib.parse import urljoin

from bs4 import BeautifulSoup, SoupStrainer

from aperix_geo.utils.html import _meta_content, _normalize_text
from aperix_geo.utils.text import is_template_title

# Generic chrome labels that are not a publishable site name.
_SITE_NAME_NOISE = frozenset(
    {
        "home",
        "homepage",
        "home page",
        "index",
        "main",
        "website",
        "官网",
        "首页",
        "主页",
        "网站",
    },
)

_HEAD_SEO_STRAINER = SoupStrainer(["title", "meta", "link"])
_JSON_LD_TYPE = re.compile(r"application/ld\+json", re.I)
_SCRIPT_STRAINER = SoupStrainer("script")
_PRODUCT_ORG_TYPES = frozenset(
    {
        "organization",
        "product",
        "softwareapplication",
        "webapplication",
        "brand",
        "corporation",
        "localbusiness",
    },
)
_FAQ_TYPES = frozenset({"faqpage", "question"})


@dataclass(frozen=True)
class SeoMetadata:
    title: str = ""
    description: str = ""
    keywords: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()
    schema_types: tuple[str, ...] = ()
    mentioned_names: tuple[str, ...] = ()
    content_type: str = ""
    site_name: str = ""
    canonical_url: str = ""
    authors: tuple[str, ...] = ()
    publisher: str = ""
    brand_names: tuple[str, ...] = ()
    categories: tuple[str, ...] = ()
    faq_items: tuple[str, ...] = ()
    speakable_text: tuple[str, ...] = ()
    breadcrumbs: tuple[str, ...] = ()


class SeoProfile(str, Enum):
    """Per-scenario SEO/GEO field subsets."""

    SUBJECT_HOMEPAGE = "subject_homepage"
    ARTICLE_DISCOVERY = "article_discovery"
    CITATION = "citation"
    CROSS_VALIDATE = "cross_validate"
    FULL = "full"


_SEO_SCALAR_FIELDS = (
    "title",
    "description",
    "content_type",
    "site_name",
    "canonical_url",
    "publisher",
)
_SEO_TUPLE_FIELDS = (
    "keywords",
    "tags",
    "schema_types",
    "mentioned_names",
    "authors",
    "brand_names",
    "categories",
    "faq_items",
    "speakable_text",
    "breadcrumbs",
)

# SUBJECT_HOMEPAGE: Setup 主体首页画像，侧重产品/赛道定位
_PROFILE_SUBJECT_HOMEPAGE = frozenset(
    {
        "title",
        "description",
        "keywords",
        "categories",
        "brand_names",
        "content_type",
        "site_name",
        "speakable_text",
        "schema_types",
    },
)

# ARTICLE_DISCOVERY: 资讯/榜单文抽竞品，侧重实体提及与 GEO 问答
_PROFILE_ARTICLE_DISCOVERY = frozenset(
    {
        "title",
        "description",
        "keywords",
        "tags",
        "categories",
        "mentioned_names",
        "brand_names",
        "faq_items",
        "speakable_text",
        "content_type",
        "publisher",
        "authors",
        "schema_types",
    },
)

# CITATION: 采样引用页 ABSA/GEO 分类，侧重来源归因与页面语义
_PROFILE_CITATION = frozenset(
    {
        "title",
        "description",
        "keywords",
        "tags",
        "categories",
        "mentioned_names",
        "brand_names",
        "faq_items",
        "speakable_text",
        "content_type",
        "site_name",
        "canonical_url",
        "publisher",
        "authors",
        "breadcrumbs",
        "schema_types",
    },
)

# CROSS_VALIDATE: 竞品官网交叉验算，身份 + 产品结构化信号
_PROFILE_CROSS_VALIDATE = frozenset(
    {
        "title",
        "description",
        "brand_names",
        "schema_types",
        "content_type",
    },
)

SEO_PROFILE_FIELDS: dict[SeoProfile, frozenset[str]] = {
    SeoProfile.SUBJECT_HOMEPAGE: _PROFILE_SUBJECT_HOMEPAGE,
    SeoProfile.ARTICLE_DISCOVERY: _PROFILE_ARTICLE_DISCOVERY,
    SeoProfile.CITATION: _PROFILE_CITATION,
    SeoProfile.CROSS_VALIDATE: _PROFILE_CROSS_VALIDATE,
    SeoProfile.FULL: frozenset(_SEO_SCALAR_FIELDS + _SEO_TUPLE_FIELDS),
}


def apply_seo_profile(meta: SeoMetadata, profile: SeoProfile) -> SeoMetadata:
    """Return a copy of *meta* keeping only fields allowed for *profile*."""
    if profile == SeoProfile.FULL:
        return meta
    allowed = SEO_PROFILE_FIELDS[profile]
    kwargs: dict[str, Any] = {}
    for name in _SEO_SCALAR_FIELDS:
        kwargs[name] = getattr(meta, name) if name in allowed else ""
    for name in _SEO_TUPLE_FIELDS:
        kwargs[name] = getattr(meta, name) if name in allowed else ()
    return SeoMetadata(**kwargs)


def seo_has_signal(meta: SeoMetadata, *, profile: SeoProfile | None = None) -> bool:
    checked = apply_seo_profile(meta, profile) if profile else meta
    return bool(
        checked.title
        or checked.description
        or checked.keywords
        or checked.tags
        or checked.mentioned_names
        or checked.brand_names
        or checked.authors
        or checked.faq_items
        or checked.speakable_text
        or checked.breadcrumbs
        or checked.categories,
    )


def _split_keywords(raw: str) -> list[str]:
    text = _normalize_text(raw)
    if not text:
        return []
    parts = re.split(r"[,，;；|/]", text)
    out: list[str] = []
    for part in parts:
        item = part.strip()
        if item and item not in out:
            out.append(item)
    return out


def _dedupe(items: list[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(item for item in items if item))


def _meta_all_values(soup: BeautifulSoup, key: str) -> list[str]:
    values: list[str] = []
    for attr in ("name", "property"):
        for tag in soup.find_all("meta", attrs={attr: key}):
            content = str(tag.get("content") or "").strip()
            if content and content not in values:
                values.append(content)
    return values


def _first_meta(soup: BeautifulSoup, *keys: str) -> str:
    for key in keys:
        value = _meta_content(soup, key)
        if value:
            return value
    return ""


def usable_site_name(raw: str) -> str:
    """Normalize a candidate site name; empty if noise / URL / handle."""
    text = _normalize_text(raw, limit=255)
    if len(text) < 2:
        return ""
    folded = text.casefold()
    if folded in _SITE_NAME_NOISE:
        return ""
    if folded.startswith(("http://", "https://", "//")):
        return ""
    if text.startswith("@"):
        return ""
    return text


def coalesce_site_name(
    *,
    site_name: str = "",
    publisher: str = "",
    breadcrumbs: tuple[str, ...] | list[str] = (),
    title: str = "",
    domain: str = "",
) -> str:
    """Pick a display site name from SEO signals (meta → publisher → crumb → title).

    Does not fall back to the bare domain — callers/UI already show domain when empty.
    """
    for candidate in (site_name, publisher):
        cleaned = usable_site_name(candidate)
        if cleaned:
            return cleaned

    for crumb in breadcrumbs[:3]:
        cleaned = usable_site_name(str(crumb or ""))
        if cleaned:
            return cleaned

    host = (domain or "").strip().lower()
    if title.strip() and host:
        from aperix_geo.utils.domains import brand_fallback, normalize_host, site_name_from_title

        derived = usable_site_name(site_name_from_title(title, domain=host))
        if not derived:
            return ""
        domain_like = {
            normalize_host(host).casefold(),
            (brand_fallback(host) or "").casefold(),
        }
        if derived.casefold() in domain_like:
            return ""
        return derived

    return ""


def _json_ld_website_name(obj: dict[str, Any]) -> str:
    types = {t.casefold() for t in _type_names(obj.get("@type"))}
    if "website" not in types:
        return ""
    return usable_site_name(
        _text_value(obj.get("name") or obj.get("alternateName"), limit=200),
    )


def _canonical_url(soup: BeautifulSoup, *, base_url: str = "") -> str:
    for tag in soup.find_all("link", rel=True, href=True):
        rel = tag.get("rel") or []
        if isinstance(rel, str):
            rel = [rel]
        if any(str(item).casefold() == "canonical" for item in rel):
            href = str(tag.get("href") or "").strip()
            if href:
                return urljoin(base_url, href) if base_url else href
    return ""


def _type_names(raw: Any) -> list[str]:
    if isinstance(raw, str):
        return [raw.split("/")[-1].strip()]
    if isinstance(raw, list):
        out: list[str] = []
        for item in raw:
            out.extend(_type_names(item))
        return out
    return []


def _text_value(raw: Any, *, limit: int = 2000) -> str:
    if isinstance(raw, str):
        return _normalize_text(raw, limit=limit)
    if isinstance(raw, (int, float)):
        return _normalize_text(str(raw), limit=limit)
    if isinstance(raw, dict):
        for key in ("text", "name", "@value", "description", "headline"):
            value = raw.get(key)
            if isinstance(value, str):
                text = _normalize_text(value, limit=limit)
                if text:
                    return text
    if isinstance(raw, list):
        for item in raw:
            text = _text_value(item, limit=limit)
            if text:
                return text
    return ""


def _name_from_thing(raw: Any) -> list[str]:
    if isinstance(raw, str):
        text = _normalize_text(raw, limit=200)
        return [text] if text else []
    if isinstance(raw, list):
        out: list[str] = []
        for item in raw:
            out.extend(_name_from_thing(item))
        return out
    if isinstance(raw, dict):
        for key in ("name", "alternateName", "legalName"):
            value = raw.get(key)
            if isinstance(value, str):
                text = _normalize_text(value, limit=200)
                if text:
                    return [text]
            if isinstance(value, list):
                return _name_from_thing(value)
        brand = raw.get("brand")
        if brand is not None:
            return _name_from_thing(brand)
    return []


def _flatten_json_ld(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, list):
        rows: list[dict[str, Any]] = []
        for item in data:
            rows.extend(_flatten_json_ld(item))
        return rows
    if not isinstance(data, dict):
        return []

    graph = data.get("@graph")
    if isinstance(graph, list):
        rows: list[dict[str, Any]] = []
        for item in graph:
            rows.extend(_flatten_json_ld(item))
        return rows
    return [data]


def _faq_item_text(question: str, answer: str) -> str:
    q = _normalize_text(question, limit=300)
    a = _normalize_text(answer, limit=800)
    if q and a:
        return f"Q: {q} A: {a}"
    if q:
        return f"Q: {q}"
    if a:
        return f"A: {a}"
    return ""


def _extract_faq(obj: dict[str, Any]) -> list[str]:
    types = {t.casefold() for t in _type_names(obj.get("@type"))}
    out: list[str] = []

    if "faqpage" in types:
        entities = obj.get("mainEntity") or obj.get("hasPart") or []
        if isinstance(entities, dict):
            entities = [entities]
        if isinstance(entities, list):
            for entity in entities:
                if isinstance(entity, dict):
                    out.extend(_extract_faq(entity))

    if "question" in types or obj.get("acceptedAnswer") is not None:
        question = _text_value(obj.get("name") or obj.get("headline"), limit=300)
        answer_obj = obj.get("acceptedAnswer")
        answer = _text_value(answer_obj, limit=800) if answer_obj is not None else ""
        item = _faq_item_text(question, answer)
        if item:
            out.append(item)
    return out


def _extract_speakable(obj: dict[str, Any]) -> list[str]:
    speakable = obj.get("speakable")
    if speakable is None:
        return []
    items = speakable if isinstance(speakable, list) else [speakable]
    out: list[str] = []
    for item in items:
        if isinstance(item, str):
            text = _normalize_text(item, limit=1000)
            if text:
                out.append(text)
            continue
        if not isinstance(item, dict):
            continue
        text = _text_value(item.get("text") or item.get("description"), limit=1000)
        if text:
            out.append(text)
    return out


def _extract_breadcrumbs(obj: dict[str, Any]) -> list[str]:
    if not any(t.casefold() == "breadcrumblist" for t in _type_names(obj.get("@type"))):
        return []
    elements = obj.get("itemListElement") or []
    if not isinstance(elements, list):
        return []
    out: list[str] = []
    for element in elements:
        if not isinstance(element, dict):
            continue
        name = _text_value(element.get("name"), limit=120)
        if not name:
            item = element.get("item") or element
            if isinstance(item, dict):
                name = _text_value(item.get("name"), limit=120)
            elif isinstance(item, str) and not item.startswith(("http://", "https://")):
                name = _normalize_text(item, limit=120)
        if name:
            out.append(name)
    return out


def _extract_product_org(obj: dict[str, Any]) -> tuple[list[str], list[str], list[str]]:
    types = {t.casefold() for t in _type_names(obj.get("@type"))}
    if not types & _PRODUCT_ORG_TYPES:
        return [], [], []

    names = _name_from_thing(obj)
    brands: list[str] = []
    brand_raw = obj.get("brand")
    if brand_raw is not None:
        brands.extend(_name_from_thing(brand_raw))

    categories: list[str] = []
    for key in ("applicationCategory", "category"):
        value = obj.get(key)
        if isinstance(value, str):
            categories.extend(_split_keywords(value))
        elif isinstance(value, list):
            for item in value:
                categories.extend(_name_from_thing(item) or _split_keywords(str(item)))

    return names, brands, categories


def _extract_json_ld(html: str) -> SeoMetadata:
    if not (html or "").strip():
        return SeoMetadata()

    soup = BeautifulSoup(html, "html.parser", parse_only=_SCRIPT_STRAINER)
    titles: list[str] = []
    descriptions: list[str] = []
    keywords: list[str] = []
    tags: list[str] = []
    schema_types: list[str] = []
    mentioned: list[str] = []
    authors: list[str] = []
    brand_names: list[str] = []
    categories: list[str] = []
    faq_items: list[str] = []
    speakable: list[str] = []
    breadcrumbs: list[str] = []
    publisher = ""
    site_name = ""

    for script in soup.find_all("script", type=_JSON_LD_TYPE):
        raw = (script.string or script.get_text() or "").strip()
        if not raw:
            continue
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            continue

        for obj in _flatten_json_ld(payload):
            for type_name in _type_names(obj.get("@type")):
                if type_name and type_name not in schema_types:
                    schema_types.append(type_name)

            for key in ("headline", "name"):
                value = obj.get(key)
                if isinstance(value, str):
                    text = _normalize_text(value, limit=500)
                    if text and text not in titles:
                        titles.append(text)

            desc = obj.get("description") or obj.get("abstract")
            if isinstance(desc, str):
                text = _normalize_text(desc, limit=2000)
                if text and text not in descriptions:
                    descriptions.append(text)

            kw = obj.get("keywords")
            if isinstance(kw, str):
                keywords.extend(_split_keywords(kw))
            elif isinstance(kw, list):
                for item in kw:
                    keywords.extend(_name_from_thing(item) or _split_keywords(str(item)))

            for key in ("about", "mentions"):
                mentioned.extend(_name_from_thing(obj.get(key)))

            if any(t.casefold() == "itemlist" for t in _type_names(obj.get("@type"))):
                if not any(t.casefold() == "breadcrumblist" for t in _type_names(obj.get("@type"))):
                    elements = obj.get("itemListElement") or []
                    if isinstance(elements, list):
                        for element in elements:
                            if isinstance(element, dict):
                                item = element.get("item") or element
                                mentioned.extend(_name_from_thing(item))

            faq_items.extend(_extract_faq(obj))
            speakable.extend(_extract_speakable(obj))
            breadcrumbs.extend(_extract_breadcrumbs(obj))

            for key in ("author", "creator"):
                authors.extend(_name_from_thing(obj.get(key)))
            pub = usable_site_name(_text_value(obj.get("publisher"), limit=200))
            if pub:
                publisher = pub

            if not site_name:
                site_name = _json_ld_website_name(obj)
            if not site_name:
                part_of = obj.get("isPartOf")
                if isinstance(part_of, dict):
                    site_name = _json_ld_website_name(part_of)
                elif isinstance(part_of, list):
                    for part in part_of:
                        if isinstance(part, dict):
                            site_name = _json_ld_website_name(part)
                            if site_name:
                                break

            org_names, brands, org_categories = _extract_product_org(obj)
            mentioned.extend(org_names)
            brand_names.extend(brands)
            categories.extend(org_categories)

    return SeoMetadata(
        title=titles[0] if titles else "",
        description=descriptions[0] if descriptions else "",
        keywords=_dedupe(keywords),
        tags=_dedupe(tags),
        schema_types=_dedupe(schema_types),
        mentioned_names=_dedupe(mentioned),
        site_name=site_name,
        publisher=publisher,
        authors=_dedupe(authors),
        brand_names=_dedupe(brand_names),
        categories=_dedupe(categories),
        faq_items=_dedupe(faq_items),
        speakable_text=_dedupe(speakable),
        breadcrumbs=_dedupe(breadcrumbs),
    )


def _extract_microdata(html: str) -> SeoMetadata:
    if not (html or "").strip():
        return SeoMetadata()

    soup = BeautifulSoup(html[:120_000], "html.parser")
    schema_types: list[str] = []
    titles: list[str] = []
    descriptions: list[str] = []
    keywords: list[str] = []
    mentioned: list[str] = []
    brand_names: list[str] = []
    faq_items: list[str] = []

    for node in soup.find_all(attrs={"itemtype": True}):
        itemtype = str(node.get("itemtype") or "")
        type_name = itemtype.split("/")[-1].strip()
        if type_name and type_name not in schema_types:
            schema_types.append(type_name)

        props: dict[str, list[str]] = {}
        scope = [node, *node.find_all(attrs={"itemprop": True})]
        for el in scope:
            prop = str(el.get("itemprop") or "").strip()
            if not prop:
                continue
            if prop not in props:
                props[prop] = []
            if el.get("itemscope") is not None and el is not node:
                continue
            value = el.get("content") or el.get("href") or el.get_text(" ", strip=True)
            text = _normalize_text(str(value or ""), limit=800)
            if text:
                props[prop].append(text)

        if props.get("headline"):
            titles.extend(props["headline"])
        if props.get("name") and type_name.casefold() in _PRODUCT_ORG_TYPES | {"article", "webpage"}:
            mentioned.extend(props["name"])
        if props.get("description"):
            descriptions.extend(props["description"])
        if props.get("keywords"):
            for raw in props["keywords"]:
                keywords.extend(_split_keywords(raw))
        if props.get("brand"):
            brand_names.extend(props["brand"])

        if type_name.casefold() in _FAQ_TYPES or props.get("acceptedAnswer"):
            question = (props.get("name") or props.get("headline") or [""])[0]
            answer = (props.get("acceptedAnswer") or props.get("text") or [""])[0]
            item = _faq_item_text(question, answer)
            if item:
                faq_items.append(item)

    return SeoMetadata(
        title=titles[0] if titles else "",
        description=descriptions[0] if descriptions else "",
        keywords=_dedupe(keywords),
        schema_types=_dedupe(schema_types),
        mentioned_names=_dedupe(mentioned),
        brand_names=_dedupe(brand_names),
        faq_items=_dedupe(faq_items),
    )


def _merge_seo(*parts: SeoMetadata) -> SeoMetadata:
    title = ""
    description = ""
    publisher = ""
    content_type = ""
    site_name = ""
    canonical_url = ""
    keywords: list[str] = []
    tags: list[str] = []
    schema_types: list[str] = []
    mentioned: list[str] = []
    authors: list[str] = []
    brand_names: list[str] = []
    categories: list[str] = []
    faq_items: list[str] = []
    speakable: list[str] = []
    breadcrumbs: list[str] = []

    for part in parts:
        if not title and part.title:
            title = part.title
        if not description and part.description:
            description = part.description
        if not publisher and part.publisher:
            publisher = part.publisher
        if not content_type and part.content_type:
            content_type = part.content_type
        if not site_name and part.site_name:
            site_name = part.site_name
        if not canonical_url and part.canonical_url:
            canonical_url = part.canonical_url
        keywords.extend(part.keywords)
        tags.extend(part.tags)
        schema_types.extend(part.schema_types)
        mentioned.extend(part.mentioned_names)
        authors.extend(part.authors)
        brand_names.extend(part.brand_names)
        categories.extend(part.categories)
        faq_items.extend(part.faq_items)
        speakable.extend(part.speakable_text)
        breadcrumbs.extend(part.breadcrumbs)

    site_name = coalesce_site_name(
        site_name=site_name,
        publisher=publisher,
        breadcrumbs=breadcrumbs,
    )

    return SeoMetadata(
        title=title,
        description=description,
        keywords=_dedupe(keywords),
        tags=_dedupe(tags),
        schema_types=_dedupe(schema_types),
        mentioned_names=_dedupe(mentioned),
        content_type=content_type,
        site_name=site_name,
        canonical_url=canonical_url,
        authors=_dedupe(authors),
        publisher=publisher,
        brand_names=_dedupe(brand_names),
        categories=_dedupe(categories),
        faq_items=_dedupe(faq_items),
        speakable_text=_dedupe(speakable),
        breadcrumbs=_dedupe(breadcrumbs),
    )


def profile_include_microdata(profile: SeoProfile) -> bool:
    """CROSS_VALIDATE only needs head meta + JSON-LD; skip Microdata body scan."""
    return profile != SeoProfile.CROSS_VALIDATE


_PARSE_CACHE: OrderedDict[tuple[str, bool], SeoMetadata] = OrderedDict()
_PARSE_CACHE_MAX = 128


def clear_seo_parse_cache() -> None:
    """Clear in-process SEO parse cache (tests)."""
    _PARSE_CACHE.clear()


def parse_seo_from_html(
    html: str,
    *,
    base_url: str = "",
    include_microdata: bool = True,
) -> SeoMetadata:
    """Extract SEO/GEO signals from HTML head meta tags, JSON-LD, and Microdata."""
    if not (html or "").strip():
        return SeoMetadata()

    digest = hashlib.sha256(html.encode("utf-8", errors="replace")).hexdigest()
    key = (digest, include_microdata)
    cached = _PARSE_CACHE.get(key)
    if cached is not None:
        _PARSE_CACHE.move_to_end(key)
        return cached

    soup = BeautifulSoup(html, "html.parser", parse_only=_HEAD_SEO_STRAINER)

    title = ""
    if soup.title:
        title = _normalize_text(soup.title.get_text(), limit=500)
    if title and is_template_title(title):
        title = ""
    if not title:
        title = _first_meta(soup, "og:title", "twitter:title")
    if title and is_template_title(title):
        title = ""

    description = _first_meta(
        soup,
        "description",
        "og:description",
        "twitter:description",
    )

    keywords: list[str] = []
    for key_name in ("keywords", "news_keywords"):
        for value in _meta_all_values(soup, key_name):
            keywords.extend(_split_keywords(value))

    tags: list[str] = []
    for value in _meta_all_values(soup, "article:tag"):
        text = _normalize_text(value, limit=120)
        if text:
            tags.append(text)

    categories: list[str] = []
    section = _first_meta(soup, "article:section")
    if section:
        categories.append(section)

    authors: list[str] = []
    for value in _meta_all_values(soup, "article:author"):
        text = _normalize_text(value, limit=200)
        if text:
            authors.append(text)
    author_meta = _first_meta(soup, "author")
    if author_meta:
        authors.append(author_meta)

    head = SeoMetadata(
        title=title,
        description=description,
        keywords=_dedupe(keywords),
        tags=_dedupe(tags),
        content_type=_first_meta(soup, "og:type"),
        site_name=_first_meta(
            soup,
            "og:site_name",
            "application-name",
            "apple-mobile-web-app-title",
        ),
        canonical_url=_canonical_url(soup, base_url=base_url),
        authors=_dedupe(authors),
        categories=_dedupe(categories),
    )

    ld = _extract_json_ld(html)
    micro = _extract_microdata(html) if include_microdata else SeoMetadata()
    result = _merge_seo(head, ld, micro)

    # Title-derived name when meta/JSON-LD are empty (needs host from base_url).
    if not result.site_name and base_url:
        from aperix_geo.utils.net import registrable_from

        host = registrable_from(base_url) or ""
        if host:
            filled = coalesce_site_name(
                site_name=result.site_name,
                publisher=result.publisher,
                breadcrumbs=result.breadcrumbs,
                title=result.title,
                domain=host,
            )
            if filled and filled != result.site_name:
                result = replace(result, site_name=filled)

    _PARSE_CACHE[key] = result
    if len(_PARSE_CACHE) > _PARSE_CACHE_MAX:
        _PARSE_CACHE.popitem(last=False)
    return result


def seo_prose_text(
    meta: SeoMetadata,
    *,
    profile: SeoProfile = SeoProfile.FULL,
    max_chars: int = 2000,
    include_schema: bool = True,
) -> str:
    """Assemble SEO/GEO fields into plain text for LLM consumption."""
    scoped = apply_seo_profile(meta, profile)
    lines: list[str] = []
    if scoped.title:
        lines.append(f"title: {scoped.title}")
    if scoped.description:
        lines.append(f"description: {scoped.description}")
    if scoped.content_type:
        lines.append(f"type: {scoped.content_type}")
    if scoped.site_name:
        lines.append(f"site: {scoped.site_name}")
    if scoped.canonical_url:
        lines.append(f"canonical: {scoped.canonical_url}")
    if scoped.authors:
        lines.append(f"authors: {', '.join(scoped.authors[:10])}")
    if scoped.publisher:
        lines.append(f"publisher: {scoped.publisher}")
    if scoped.keywords:
        lines.append(f"keywords: {', '.join(scoped.keywords[:20])}")
    if scoped.tags:
        lines.append(f"tags: {', '.join(scoped.tags[:20])}")
    if scoped.categories:
        lines.append(f"categories: {', '.join(scoped.categories[:10])}")
    if scoped.brand_names:
        lines.append(f"brands: {', '.join(scoped.brand_names[:20])}")
    if scoped.mentioned_names:
        lines.append(f"mentions: {', '.join(scoped.mentioned_names[:30])}")
    if scoped.breadcrumbs:
        lines.append(f"breadcrumbs: {' > '.join(scoped.breadcrumbs[:10])}")
    if scoped.faq_items:
        lines.append("faq:")
        for item in scoped.faq_items[:8]:
            lines.append(f"- {item}")
    if scoped.speakable_text:
        lines.append(f"speakable: {' | '.join(scoped.speakable_text[:5])}")
    if include_schema and scoped.schema_types:
        lines.append(f"schema: {', '.join(scoped.schema_types[:10])}")
    text = "\n".join(lines).strip()
    if max_chars and len(text) > max_chars:
        return text[:max_chars].rstrip()
    return text
