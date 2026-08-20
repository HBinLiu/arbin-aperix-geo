"""Persist ABSA open-set brands into tb_brands during sampling parse."""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from aperix_geo.db.models import BrandSource, Subject
from aperix_geo.services.brand.cache import remember_brand_row_domains
from aperix_geo.services.brand.catalog import BrandSyncContext
from aperix_geo.services.brand.domain import extract_domain_from_text_for_brand, resolve_brand_domain
from aperix_geo.services.brand.keys import configured_brand_keys
from aperix_geo.services.brand.resolve import merge_brand_aliases, normalize_brand_key, resolve_or_create_brand
from aperix_geo.services.brand.verify import homepage_matches_both_brands
from aperix_geo.services.competitor.enrich import enrich_open_set_brand_aliases
from aperix_geo.services.competitor.head_fetch import fetch_site_heads
from aperix_geo.services.competitor.types import SiteHead
from aperix_geo.services.sampling.mentions import absa_competitor_keys, absa_own_keys, competitor_entries, own_names
from aperix_geo.utils.net import brand_from, registrable_from

logger = logging.getLogger(__name__)


def _competitor_alias_list(subject: Subject) -> list[str]:
    out: list[str] = []
    for competitor in subject.competitors or []:
        for alias in competitor.aliases or []:
            text = str(alias or "").strip()
            if text:
                out.append(text)
    return out


def _is_known_brand_label(
    label: str,
    *,
    configured_keys: set[str],
    catalog: BrandSyncContext,
) -> bool:
    """闭集键或 tb_brands 已有品牌名/aliases 命中则视为已知品牌，不开新开集行。"""
    key = normalize_brand_key(label)
    if not key or key in configured_keys:
        return True
    return catalog.catalog.find_by_name_or_alias(label) is not None


def _merge_open_set_alias_on_verified_domain(
    label: str,
    domain_key: str,
    *,
    sync_ctx: BrandSyncContext,
    subject_id: UUID,
    head: SiteHead | None = None,
) -> bool:
    """同域已有开集行且首页同时识别新旧名称 → 合并为 aliases，不新建 brand。"""
    existing = sync_ctx.catalog.find_by_domain(domain_key)
    if existing is None or existing.entity_kind != "other":
        return False
    label_key = normalize_brand_key(label)
    if label_key == normalize_brand_key(existing.brand):
        return True
    for alias in existing.aliases or []:
        if normalize_brand_key(str(alias)) == label_key:
            return True
    if not homepage_matches_both_brands(
        domain_key,
        label,
        existing.brand,
        head=head,
    ):
        return False
    existing.aliases = merge_brand_aliases(existing.aliases or [], [label])
    sync_ctx.catalog.register(existing)
    remember_brand_row_domains(subject_id=subject_id, brand=existing)
    logger.debug(
        "开集品牌别名合并 subject=%s brand=%r alias=%r domain=%s",
        subject_id,
        existing.brand,
        label,
        domain_key,
    )
    return True


def persist_open_brands_from_absa(
    db: Session,
    *,
    subject: Subject,
    response_absa: dict[str, Any],
    raw_text: str,
    url_hosts: list[str] | None = None,
) -> int:
    """Upsert subject-scoped open-set brand rows from ABSA output (no cross-validation)."""
    others = dict(response_absa.get("other_brands_sentiment_absa") or {})
    if not others:
        return 0

    from aperix_geo.services.analysis.entity import own_entity

    own = own_entity(subject)
    own_brand = (subject.brand or own.label).strip()
    own_match_names = own_names(subject)
    own_brand_names, own_absa_keys = absa_own_keys(
        own_brand=own_brand,
        own_match_names=own_match_names,
        entity_label=own.label,
    )
    competitors = competitor_entries(subject)
    competitor_brand_names, competitor_absa_keys = absa_competitor_keys(competitors)
    competitor_alias_list = _competitor_alias_list(subject)
    configured_keys = configured_brand_keys(
        own_brand=own_brand,
        own_match_names=own_match_names,
        own_absa_keys=own_absa_keys,
        competitor_brand_names=competitor_brand_names,
        competitor_absa_keys=competitor_absa_keys,
        subject_aliases=[str(x) for x in (subject.aliases or []) if str(x).strip()],
        competitor_aliases=competitor_alias_list,
    )
    configured_domains = {
        registrable_from(c.domain)
        for c in (subject.competitors or [])
        if c.domain and registrable_from(c.domain)
    }

    sync_ctx = BrandSyncContext.load(db, subject_id=subject.id)
    urls = list(url_hosts or [])
    persisted = 0

    for name, entry in others.items():
        label = str(name or "").strip()
        if not label or not isinstance(entry, dict) or not entry.get("mentioned"):
            continue
        if _is_known_brand_label(label, configured_keys=configured_keys, catalog=sync_ctx):
            continue

        domain = extract_domain_from_text_for_brand(raw_text, label, urls)
        domain = brand_from(domain) if domain else ""
        if not domain:
            domain = resolve_brand_domain(
                db,
                subject_id=subject.id,
                brand=label,
                raw_text=raw_text,
                urls=urls,
                sync_ctx=sync_ctx,
            )
        domain_key = registrable_from(domain) if domain else ""
        if domain_key and domain_key in configured_domains:
            continue

        head: SiteHead | None = None
        if domain_key:
            head = fetch_site_heads([domain_key]).get(domain_key)
            if _merge_open_set_alias_on_verified_domain(
                label,
                domain_key,
                sync_ctx=sync_ctx,
                subject_id=subject.id,
                head=head,
            ):
                persisted += 1
                continue

        aliases: list[str] = []
        if domain_key:
            aliases = enrich_open_set_brand_aliases(
                brand=label,
                domain=domain,
                head=head,
            )

        resolve_or_create_brand(
            db,
            subject_id=subject.id,
            brand=label,
            domain=domain or "",
            aliases=aliases,
            entity_kind="other",
            source=BrandSource.sampling_open_set,
            catalog=sync_ctx.catalog,
            open_set_brand=True,
        )
        persisted += 1
        logger.debug(
            "开集品牌已写入 tb_brands subject=%s brand=%r domain=%s",
            subject.id,
            label,
            domain_key or "(empty)",
        )

    if persisted:
        db.flush()
    return persisted


def promote_confirmed_open_brands_from_absa(
    db: Session,
    *,
    subject: Subject,
    response_absa: dict[str, Any],
    raw_text: str,
    url_hosts: list[str] | None = None,
) -> int:
    """Persist tb_brands only for ABSA-confirmed open mentions from the commit plan."""
    events = response_absa.get("mention_commit_events")
    if not isinstance(events, list):
        return persist_open_brands_from_absa(
            db,
            subject=subject,
            response_absa=response_absa,
            raw_text=raw_text,
            url_hosts=url_hosts,
        )

    committed_labels = [
        str(item.get("text") or "").strip()
        for item in events
        if isinstance(item, dict) and item.get("status") == "committed" and str(item.get("text") or "").strip()
    ]
    if not committed_labels:
        return 0

    committed_keys = {normalize_brand_key(label) for label in committed_labels}
    others_raw = response_absa.get("other_brands_sentiment_absa") or {}
    filtered_others: dict[str, Any] = {}
    for name, entry in others_raw.items():
        if normalize_brand_key(str(name)) in committed_keys:
            filtered_others[str(name)] = entry
    present = {normalize_brand_key(str(name)) for name in filtered_others}
    for label in committed_labels:
        key = normalize_brand_key(label)
        if key not in present:
            filtered_others[label] = {"mentioned": True, "score": None, "evidence": label}
            present.add(key)

    return persist_open_brands_from_absa(
        db,
        subject=subject,
        response_absa={
            "analysis_source": response_absa.get("analysis_source"),
            "other_brands_sentiment_absa": filtered_others,
        },
        raw_text=raw_text,
        url_hosts=url_hosts,
    )
