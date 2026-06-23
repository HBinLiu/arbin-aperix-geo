"""Promote open-set brands to configured competitors (signal migration only)."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from aperix_geo.db.models import Brand, BrandSource, Competitor, EntityKind, LLMResponseSignal, Subject
from aperix_geo.services.brand.resolve import normalize_brand_key
from aperix_geo.services.sampling.cache import clear_subject_sampling_cache
from aperix_geo.services.subject.domain_fields import prepare_domain_and_website_url
from aperix_geo.services.subject.labels import competitor_rank_label
from aperix_geo.utils.net import ensure_brand, registrable_from


class PromoteBrandError(ValueError):
    """Business rule violation when confirming a potential competitor."""


@dataclass(frozen=True)
class PromoteBrandResult:
    competitor_id: UUID
    brand_id: UUID
    entity_label: str
    signals_migrated: int
    signals_dropped: int


def _competitor_conflicts(subject: Subject, *, brand: Brand) -> None:
    brand_key = normalize_brand_key(brand.brand)
    domain_key = registrable_from(brand.domain) if brand.domain else ""
    for existing in subject.competitors or []:
        existing_domain = registrable_from(existing.domain) if existing.domain else ""
        if domain_key and existing_domain and domain_key == existing_domain:
            raise PromoteBrandError("该域名已是配置竞品")
        existing_brand_key = normalize_brand_key(existing.brand)
        if brand_key and existing_brand_key and brand_key == existing_brand_key:
            raise PromoteBrandError("该品牌已是配置竞品")


def migrate_open_brand_signals_to_competitor(
    db: Session,
    *,
    subject_id: UUID,
    brand_id: UUID,
    competitor_id: UUID,
    entity_label: str,
) -> tuple[int, int]:
    """Rewrite historical other signals to competitor entity_id (plan A)."""
    competitor_entity_id = str(competitor_id)
    other_signals = list(
        db.execute(
            select(LLMResponseSignal).where(
                LLMResponseSignal.subject_id == subject_id,
                LLMResponseSignal.brand_id == brand_id,
                LLMResponseSignal.entity_kind == EntityKind.other.value,
            )
        )
        .scalars()
        .all()
    )
    if not other_signals:
        return 0, 0

    response_ids = {row.response_id for row in other_signals}
    existing_competitor_rows = {
        row.response_id: row
        for row in db.execute(
            select(LLMResponseSignal).where(
                LLMResponseSignal.response_id.in_(response_ids),
                LLMResponseSignal.entity_id == competitor_entity_id,
            )
        )
        .scalars()
        .all()
    }

    migrated = 0
    dropped = 0
    for signal in other_signals:
        conflict = existing_competitor_rows.get(signal.response_id)
        if conflict is not None:
            db.delete(signal)
            dropped += 1
            continue
        signal.entity_id = competitor_entity_id
        signal.entity_kind = EntityKind.competitor.value
        signal.entity_label = entity_label
        existing_competitor_rows[signal.response_id] = signal
        migrated += 1
    return migrated, dropped


def promote_open_brand_to_competitor(
    db: Session,
    *,
    subject: Subject,
    brand_id: UUID,
) -> PromoteBrandResult:
    """Confirm a potential competitor: tb_competitors + brand row + signal migration."""
    brand = db.execute(
        select(Brand).where(Brand.id == brand_id, Brand.subject_id == subject.id)
    ).scalar_one_or_none()
    if brand is None:
        raise PromoteBrandError("品牌不存在")
    if brand.entity_kind != EntityKind.other.value:
        raise PromoteBrandError("仅可晋升开集品牌")

    _competitor_conflicts(subject, brand=brand)

    domain_raw = (brand.domain or "").strip()
    website_url = (brand.website_url or "").strip()
    if domain_raw:
        domain, website_url = prepare_domain_and_website_url(
            domain_raw,
            website_url,
            probe=not bool(website_url),
        )
    else:
        domain = ""
        website_url = ""

    display_brand = ensure_brand(brand.brand, domain=domain)
    alias_list = [str(a).strip() for a in (brand.aliases or []) if str(a).strip()]

    competitor = Competitor(
        subject_id=subject.id,
        domain=domain,
        website_url=website_url,
        brand=display_brand,
        aliases=alias_list,
        summary=(brand.summary or "").strip(),
        cross_validate_score=brand.cross_validate_score,
        cross_validate_reason=(brand.cross_validate_reason or "").strip(),
        cross_validated_at=brand.cross_validated_at,
    )
    subject.competitors.append(competitor)
    db.flush()

    entity_label = competitor_rank_label(brand=display_brand, domain=domain)
    brand.entity_kind = EntityKind.competitor.value
    brand.brand = display_brand
    brand.domain = domain
    brand.website_url = website_url
    brand.aliases = alias_list
    if not brand.source:
        brand.source = BrandSource.setup

    migrated, dropped = migrate_open_brand_signals_to_competitor(
        db,
        subject_id=subject.id,
        brand_id=brand.id,
        competitor_id=competitor.id,
        entity_label=entity_label,
    )
    clear_subject_sampling_cache(subject.id)
    return PromoteBrandResult(
        competitor_id=competitor.id,
        brand_id=brand.id,
        entity_label=entity_label,
        signals_migrated=migrated,
        signals_dropped=dropped,
    )
