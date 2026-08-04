"""Domain content-type classification (Shallalist codes via seed + heuristics)."""

from __future__ import annotations

from typing import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from aperix_geo.db.models import DomainProfile
from aperix_geo.services.domain.seeds import seed_domain_type
from aperix_geo.services.domain.taxonomy import DEFAULT_DOMAIN_TYPE, normalize_domain_type
from aperix_geo.utils.net import registrable_from

# Seed/heuristic hits are final. Pending rows use source=""; unresolved end as other.
_RESOLVED_SOURCES = frozenset({"seed"})


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


def classify_domains(db: Session, domains: Iterable[str]) -> dict[str, str]:
    """Classify domains via seed map + TLD heuristics; unresolved → ``other``."""
    pending = ensure_domain_profiles(db, domains)
    if not pending:
        return domain_types_for(db, domains)

    rows = {
        row.domain: row
        for row in db.execute(select(DomainProfile).where(DomainProfile.domain.in_(pending))).scalars().all()
    }
    for domain in pending:
        row = rows.get(domain)
        if row is None or _is_resolved(row):
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
