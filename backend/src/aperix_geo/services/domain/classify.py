"""Domain content-type classification (Shallalist codes)."""

from __future__ import annotations

import logging
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from aperix_geo.db.models import DomainProfile
from aperix_geo.services.domain.seeds import seed_domain_type
from aperix_geo.services.domain.taxonomy import DEFAULT_DOMAIN_TYPE, normalize_domain_type
from aperix_geo.utils.net import registrable_from

logger = logging.getLogger(__name__)

# Pending ML uses source=""; seed/piedomains are final. "other" is fallback after ML miss.
_RESOLVED_SOURCES = frozenset({"seed", "piedomains"})


def _normalize_domain(domain: str) -> str:
    raw = (domain or "").strip().lower()
    if not raw:
        return ""
    return registrable_from(raw) or raw


def _is_resolved(row: DomainProfile) -> bool:
    return row.source in _RESOLVED_SOURCES


def ensure_domain_profiles(db: Session, domains: Iterable[str]) -> list[str]:
    """Upsert profile rows; apply seed types immediately. Returns domains still pending ML."""
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


def classify_domains(db: Session, domains: Iterable[str]) -> dict[str, str]:
    """Classify pending domains via seed, then optional piedomains.

    Domains still unresolved after the attempt stay ``other`` (source=other).
    """
    pending = ensure_domain_profiles(db, domains)
    if not pending:
        return domain_types_for(db, domains)

    predictions = _classify_with_piedomains(pending)
    rows = {
        row.domain: row
        for row in db.execute(select(DomainProfile).where(DomainProfile.domain.in_(pending))).scalars().all()
    }
    if predictions:
        for domain, label in predictions.items():
            normalized = normalize_domain_type(label)
            row = rows.get(domain)
            if row is None or _is_resolved(row):
                continue
            if normalized == DEFAULT_DOMAIN_TYPE and not (label or "").strip():
                continue
            row.domain_type = normalized
            row.source = "piedomains"

    for domain in pending:
        row = rows.get(domain)
        if row is None or _is_resolved(row):
            continue
        row.domain_type = DEFAULT_DOMAIN_TYPE
        row.source = "other"

    return domain_types_for(db, domains)


def _classify_with_piedomains(domains: list[str]) -> dict[str, str]:
    if not domains:
        return {}
    try:
        from piedomains import DomainClassifier  # type: ignore[import-not-found]
    except Exception:
        logger.debug("piedomains not installed; skip ML domain classification")
        return {}

    try:
        classifier = DomainClassifier()
        result = classifier.classify_by_text(domains)
    except Exception:
        logger.warning("piedomains classify_by_text failed", exc_info=True)
        return {}

    out: dict[str, str] = {}
    # API may return DataFrame or list[dict]
    if hasattr(result, "iterrows"):
        for _, row in result.iterrows():
            domain = _normalize_domain(str(row.get("domain", "")))
            label = str(row.get("pred_label") or row.get("category") or "").strip()
            if domain and label:
                out[domain] = label
        return out

    if isinstance(result, list):
        for item in result:
            if not isinstance(item, dict):
                continue
            domain = _normalize_domain(str(item.get("domain", "")))
            label = str(item.get("pred_label") or item.get("category") or "").strip()
            if domain and label:
                out[domain] = label
    return out


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
