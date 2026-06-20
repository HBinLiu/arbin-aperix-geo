"""Filter open-set ABSA brands to subject-relative competitors via cross-validate."""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from aperix_geo.config import get_settings
from aperix_geo.db.models import Brand, BrandSource, Subject, SubjectType
from aperix_geo.services.brand.domain import extract_domain_from_text_for_brand, resolve_brand_domain
from aperix_geo.services.brand.resolve import (
    brand_passes_cross_validate,
    find_brand_by_name_or_alias,
    resolve_or_create_brand,
)
from aperix_geo.services.competitor.cross_validate import run_cross_validate
from aperix_geo.services.competitor.profile import profile_from_dict
from aperix_geo.services.competitor.types import CandidateMeta, CandidatePool, NicheProfile
from aperix_geo.services.sampling.cache.cross_validate import (
    get_cross_validate_score_cached,
    set_cross_validate_score_cached,
)
from aperix_geo.utils.cache import run_single_flight
from aperix_geo.utils.domains import registrable_domain

logger = logging.getLogger(__name__)

_CROSS_VALIDATE_DONE = object()


def subject_niche_profile(subject: Subject) -> NicheProfile:
    data = dict(subject.niche_profile or {})
    if data:
        return profile_from_dict(data)
    entity = subject.domain or subject.brand or str(subject.id)
    return profile_from_dict(
        {
            "company": subject.brand or entity,
            "industry": "未知行业",
            "features": "",
            "customers": "",
            "keywords": "",
        }
    )


def subject_target_domain(subject: Subject) -> str:
    if subject.type == SubjectType.domain and subject.domain:
        return registrable_domain(subject.domain) or subject.domain
    if subject.website_url:
        root = registrable_domain(subject.website_url)
        if root:
            return root
    return ""


@dataclass(frozen=True)
class _PendingOther:
    label: str
    entry: dict[str, Any]
    domain: str


def _existing_open_brand(
    db: Session,
    *,
    subject_id: UUID,
    label: str,
) -> Brand | None:
    return find_brand_by_name_or_alias(db, subject_id=subject_id, brand=label)


def _apply_cross_validate_score(
    db: Session,
    *,
    subject: Subject,
    item: _PendingOther,
    domain_key: str,
    score: float,
    reason: str,
    pass_score: float,
    kept: dict[str, dict[str, Any]],
) -> None:
    set_cross_validate_score_cached(
        subject_id=subject.id,
        domain=domain_key,
        score=score,
        reason=reason,
    )
    if score < pass_score:
        logger.debug(
            "开集品牌未通过交叉验算 subject=%s brand=%r domain=%s score=%s",
            subject.id,
            item.label,
            domain_key,
            score,
        )
        return
    resolve_or_create_brand(
        db,
        subject_id=subject.id,
        brand=item.label,
        domain=item.domain,
        entity_kind="other",
        source=BrandSource.sampling_open_set,
        cross_validate_score=score,
        cross_validate_reason=reason,
    )
    kept[item.label] = item.entry


def _resolve_score_from_cache_or_db(
    db: Session,
    *,
    subject: Subject,
    item: _PendingOther,
    domain_key: str,
    pass_score: float,
    kept: dict[str, dict[str, Any]],
) -> bool:
    """Return True when the domain no longer needs a fresh cross-validate LLM call."""
    existing = _existing_open_brand(db, subject_id=subject.id, label=item.label)
    if existing is not None and existing.cross_validate_score is not None:
        if brand_passes_cross_validate(existing, min_score=pass_score):
            kept[item.label] = item.entry
        return True

    cached = get_cross_validate_score_cached(subject_id=subject.id, domain=domain_key)
    if cached is not None:
        _apply_cross_validate_score(
            db,
            subject=subject,
            item=item,
            domain_key=domain_key,
            score=float(cached["score"]),
            reason=str(cached.get("reason") or ""),
            pass_score=pass_score,
            kept=kept,
        )
        return True
    return False


def _validate_pending_batch(
    db: Session,
    *,
    subject: Subject,
    profile: NicheProfile,
    pending: list[_PendingOther],
    pass_score: float,
    kept: dict[str, dict[str, Any]],
) -> None:
    target_domain = subject_target_domain(subject)
    if not target_domain or not pending:
        return

    by_domain: dict[str, _PendingOther] = {}
    for item in pending:
        key = registrable_domain(item.domain)
        if key:
            by_domain.setdefault(key, item)

    if not by_domain:
        return

    unresolved: dict[str, _PendingOther] = {}
    for domain_key, item in by_domain.items():
        if not _resolve_score_from_cache_or_db(
            db,
            subject=subject,
            item=item,
            domain_key=domain_key,
            pass_score=pass_score,
            kept=kept,
        ):
            unresolved[domain_key] = item

    if not unresolved:
        return

    domain_keys = sorted(unresolved.keys())
    digest = hashlib.sha256(f"{subject.id}|{'|'.join(domain_keys)}".encode()).hexdigest()

    def _read_flight_cache() -> object | None:
        for domain_key in domain_keys:
            item = unresolved[domain_key]
            if not _resolve_score_from_cache_or_db(
                db,
                subject=subject,
                item=item,
                domain_key=domain_key,
                pass_score=pass_score,
                kept=kept,
            ):
                return None
        return _CROSS_VALIDATE_DONE

    def _fetch_cross_validate() -> object:
        pool = CandidatePool(
            domains=domain_keys,
            by_domain={
                domain: CandidateMeta(domain=domain, brand=unresolved[domain].label, website_url="")
                for domain in domain_keys
            },
        )
        result = run_cross_validate(
            profile,
            target_domain=target_domain,
            target_website_url=subject.website_url or "",
            pool=pool,
        )
        scores = {registrable_domain(row.domain): row for row in result.scores}
        for domain_key in domain_keys:
            item = unresolved[domain_key]
            row = scores.get(domain_key)
            score = row.score if row is not None else 0.0
            reason = row.reason if row is not None else "交叉验算未返回分数"
            _apply_cross_validate_score(
                db,
                subject=subject,
                item=item,
                domain_key=domain_key,
                score=float(score),
                reason=reason,
                pass_score=pass_score,
                kept=kept,
            )
        db.flush()
        return _CROSS_VALIDATE_DONE

    run_single_flight(
        digest,
        wait_s=120.0,
        read_cache=_read_flight_cache,
        fetch=_fetch_cross_validate,
        lock_prefix="aperix:cross_validate:lock:",
    )


def filter_competitive_other_brands(
    db: Session,
    *,
    subject: Subject,
    others: dict[str, Any],
    raw_text: str,
    url_hosts: list[str] | None = None,
) -> dict[str, dict[str, Any]]:
    """Keep only open-set brands that pass stored or fresh cross-validation."""
    if not others:
        return {}

    settings = get_settings()
    pass_score = settings.competitor_cross_validate_pass_score
    profile = subject_niche_profile(subject)
    configured_domains = {
        registrable_domain(c.domain)
        for c in (subject.competitors or [])
        if c.domain
    }
    configured_names = {
        (c.brand or "").strip().casefold()
        for c in (subject.competitors or [])
        if (c.brand or "").strip()
    }
    own_name = (subject.brand or "").strip().casefold()

    kept: dict[str, dict[str, Any]] = {}
    pending: list[_PendingOther] = []
    urls = list(url_hosts or [])

    for name, entry in others.items():
        label = str(name or "").strip()
        if not label or not isinstance(entry, dict) or not entry.get("mentioned"):
            continue
        label_key = label.casefold()
        if label_key == own_name or label_key in configured_names:
            continue

        domain = extract_domain_from_text_for_brand(raw_text, label, urls)
        if not domain:
            domain = resolve_brand_domain(
                db,
                subject_id=subject.id,
                brand=label,
                raw_text=raw_text,
                urls=urls,
                allow_search=False,
            )
        if domain and registrable_domain(domain) in configured_domains:
            continue

        existing = _existing_open_brand(db, subject_id=subject.id, label=label)
        if existing is not None and existing.cross_validate_score is not None:
            if brand_passes_cross_validate(existing, min_score=pass_score):
                kept[label] = entry
            continue

        if not domain:
            logger.debug("开集品牌跳过（无域名） subject=%s brand=%r", subject.id, label)
            continue

        pending.append(_PendingOther(label=label, entry=entry, domain=domain))

    _validate_pending_batch(
        db,
        subject=subject,
        profile=profile,
        pending=pending,
        pass_score=pass_score,
        kept=kept,
    )
    return kept


def filter_open_brands_in_response_absa(
    db: Session,
    *,
    subject: Subject,
    response_absa: dict[str, Any],
    raw_text: str,
    url_hosts: list[str] | None = None,
) -> dict[str, Any]:
    """Run cross-validation on open-set ABSA brands once; return updated response_absa."""
    others = dict(response_absa.get("other_brands_sentiment_absa") or {})
    if not others:
        return response_absa
    kept = filter_competitive_other_brands(
        db,
        subject=subject,
        others=others,
        raw_text=raw_text,
        url_hosts=url_hosts,
    )
    return {**response_absa, "other_brands_sentiment_absa": kept}
