"""Domain content-type classification: seed → homepage SEO rules → DeepSeek."""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from aperix_geo.db.models import DomainProfile
from aperix_geo.services.crawl import page_crawl_settings
from aperix_geo.services.crawl.seo import SeoMetadata, SeoProfile, seo_prose_text
from aperix_geo.services.domain.type_rules import domain_type_from_homepage_seo
from aperix_geo.services.domain.seeds import seed_domain_type
from aperix_geo.services.domain.site_name import HomepageProfile, fetch_homepage_profile
from aperix_geo.services.domain.taxonomy import DEFAULT_DOMAIN_TYPE, DOMAIN_TYPES, normalize_domain_type
from aperix_geo.services.providers import LLMProviderError, chat_completion
from aperix_geo.services.providers.prompts import (
    domain_type_classify_system_prompt,
    domain_type_classify_user_content,
)
from aperix_geo.utils.json import extract_json_object
from aperix_geo.utils.net import registrable_from

logger = logging.getLogger(__name__)

# Final sources — do not re-enqueue for type classify
_RESOLVED_SOURCES = frozenset({"seed", "homepage", "llm", "other"})


def _normalize_domain(domain: str) -> str:
    raw = (domain or "").strip().lower()
    if not raw:
        return ""
    return registrable_from(raw) or raw


def _is_resolved(row: DomainProfile) -> bool:
    return row.source in _RESOLVED_SOURCES


def ensure_domain_profiles(db: Session, domains: Iterable[str]) -> list[str]:
    """Upsert profile rows; apply seed/heuristics. Returns domains still pending."""
    keys = sorted({_normalize_domain(d) for d in domains if _normalize_domain(d)})
    if not keys:
        return []

    existing = {
        row.domain: row
        for row in db.execute(select(DomainProfile).where(DomainProfile.domain.in_(keys))).scalars().all()
    }
    pending: list[str] = []
    for domain in keys:
        row = existing.get(domain)
        raw_seed = (seed_domain_type(domain) or "").strip()
        if row is None:
            if raw_seed:
                db.add(
                    DomainProfile(
                        domain=domain,
                        domain_type=normalize_domain_type(raw_seed),
                        source="seed",
                    )
                )
            else:
                db.add(
                    DomainProfile(
                        domain=domain,
                        domain_type=DEFAULT_DOMAIN_TYPE,
                        source="",
                    )
                )
                pending.append(domain)
            continue
        if _is_resolved(row):
            continue
        if raw_seed:
            row.domain_type = normalize_domain_type(raw_seed)
            row.source = "seed"
            continue
        row.domain_type = normalize_domain_type(row.domain_type) or DEFAULT_DOMAIN_TYPE
        pending.append(domain)
    return pending


def domain_types_for(db: Session, domains: Iterable[str]) -> dict[str, str]:
    keys = sorted({_normalize_domain(d) for d in domains if _normalize_domain(d)})
    if not keys:
        return {}
    rows = db.execute(select(DomainProfile).where(DomainProfile.domain.in_(keys))).scalars().all()
    return {row.domain: normalize_domain_type(row.domain_type) for row in rows}


def domain_site_names_for(db: Session, domains: Iterable[str]) -> dict[str, str]:
    keys = sorted({_normalize_domain(d) for d in domains if _normalize_domain(d)})
    if not keys:
        return {}
    rows = db.execute(select(DomainProfile).where(DomainProfile.domain.in_(keys))).scalars().all()
    return {row.domain: str(row.site_name or "").strip() for row in rows if str(row.site_name or "").strip()}


def remember_domain_site_names(db: Session, names: dict[str, str]) -> None:
    """Write DomainProfile.site_name (fill empty; allow correcting headline-like values)."""
    cleaned: dict[str, str] = {}
    for raw_domain, raw_name in names.items():
        domain = _normalize_domain(raw_domain)
        name = str(raw_name or "").strip()[:255]
        if domain and name:
            cleaned[domain] = name
    if not cleaned:
        return

    ensure_domain_profiles(db, cleaned.keys())
    rows = {
        row.domain: row
        for row in db.execute(select(DomainProfile).where(DomainProfile.domain.in_(list(cleaned)))).scalars().all()
    }
    for domain, name in cleaned.items():
        row = rows.get(domain)
        if row is None:
            continue
        existing = str(row.site_name or "").strip()
        if not existing:
            row.site_name = name
            continue
        # 已有值像文章标题（偏长），首页品牌名更短时允许纠正
        if len(existing) > 20 and len(name) <= 20 and len(name) < len(existing):
            row.site_name = name


def classify_domain_type_with_llm(*, domain: str, meta: SeoMetadata | None) -> str:
    """DeepSeek closed-set classify; return normalized type or empty on failure."""
    prose = ""
    if meta is not None:
        prose = seo_prose_text(meta, profile=SeoProfile.SUBJECT_HOMEPAGE, max_chars=1500)
    messages = [
        {"role": "system", "content": domain_type_classify_system_prompt(DOMAIN_TYPES)},
        {
            "role": "user",
            "content": domain_type_classify_user_content(domain=domain, seo_prose=prose),
        },
    ]
    try:
        text, _, _ = chat_completion(messages, temperature=0.0, json_mode=True)
        data = extract_json_object(text)
        if not isinstance(data, dict):
            return ""
        raw = str(data.get("domain_type") or "").strip().lower()
        if not raw:
            return ""
        normalized = normalize_domain_type(raw)
        # Reject inventing codes that collapse to other unless model said other
        if normalized == DEFAULT_DOMAIN_TYPE and raw != DEFAULT_DOMAIN_TYPE:
            return ""
        return normalized
    except (LLMProviderError, TypeError, ValueError, KeyError) as exc:
        logger.warning("domain_type LLM classify failed domain=%s err=%s", domain, exc)
        return ""


def classify_domains(db: Session, domains: Iterable[str]) -> dict[str, str]:
    """Classify via seed → homepage SEO rules → DeepSeek; unresolved → ``other``."""
    pending = ensure_domain_profiles(db, domains)
    if not pending:
        return domain_types_for(db, domains)

    crawl = page_crawl_settings()
    workers = max(1, min(len(pending), crawl.concurrency))

    def run_one(host: str) -> HomepageProfile:
        return fetch_homepage_profile(host)

    profiles: dict[str, HomepageProfile] = {}
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for profile in pool.map(run_one, pending):
            if profile.domain:
                profiles[profile.domain] = profile

    site_names = {
        host: profile.site_name
        for host, profile in profiles.items()
        if profile.site_name
    }
    if site_names:
        remember_domain_site_names(db, site_names)

    rows = {
        row.domain: row
        for row in db.execute(select(DomainProfile).where(DomainProfile.domain.in_(pending))).scalars().all()
    }
    for domain in pending:
        row = rows.get(domain)
        if row is None or _is_resolved(row):
            continue
        profile = profiles.get(domain)
        meta = profile.meta if profile else None

        ruled = domain_type_from_homepage_seo(domain, meta)
        if ruled:
            row.domain_type = ruled
            row.source = "homepage"
            continue

        llm_type = classify_domain_type_with_llm(domain=domain, meta=meta)
        if llm_type:
            row.domain_type = llm_type
            row.source = "llm"
            continue

        row.domain_type = DEFAULT_DOMAIN_TYPE
        row.source = "other"

    return domain_types_for(db, domains)


def maybe_enqueue_domain_type_classify(domains: Iterable[str]) -> None:
    keys = sorted({_normalize_domain(d) for d in domains if _normalize_domain(d)})
    if not keys:
        return
    from aperix_geo.utils.cache.redis_kv import redis_set_nx

    # Coalesce bursts of the same domain within an hour
    to_send: list[str] = []
    for domain in keys:
        if redis_set_nx(f"aperix:domain:type:{domain}", ttl_s=3600):
            to_send.append(domain)
    if not to_send:
        return

    from aperix_geo.tasks.domain import classify_domain_types

    classify_domain_types.delay(to_send)
