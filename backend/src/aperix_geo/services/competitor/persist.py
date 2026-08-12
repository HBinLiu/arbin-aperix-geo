"""竞品列表持久化（设置向导 finalize 与 CRUD 共用）。"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from aperix_geo.db.models import Competitor, Subject
from aperix_geo.schemas.catalog import CompetitorItem
from aperix_geo.services.competitor.keys import competitor_match_key, find_competitor_conflict
from aperix_geo.services.billing.quota import assert_competitor_capacity
from aperix_geo.services.subject.domain_fields import prepare_domain_and_website_url
from aperix_geo.utils.net import ensure_brand


class DuplicateCompetitorError(Exception):
    pass


class CompetitorNotFoundError(Exception):
    pass


class InvalidCompetitorError(Exception):
    pass


def _normalize_competitor_items(
    competitors: list[CompetitorItem],
) -> list[dict[str, Any]]:
    seen_domains: set[str] = set()
    seen_brands: set[str] = set()
    normalized: list[dict[str, Any]] = []

    for item in competitors:
        summary = (item.summary or "").strip()
        domain_raw = (item.domain or "").strip()
        if domain_raw:
            user_url = (item.website_url or "").strip()
            domain, website_url = prepare_domain_and_website_url(
                domain_raw,
                user_url,
                probe=not bool(user_url),
            )
            if not domain or len(domain) < 3 or domain in seen_domains:
                continue
            seen_domains.add(domain)
            brand = ensure_brand(item.brand, domain=domain)
            normalized.append(
                {
                    "domain": domain,
                    "website_url": website_url,
                    "brand": brand,
                    "aliases": [str(a).strip() for a in (item.aliases or []) if str(a).strip()],
                    "summary": summary,
                }
            )
            continue

        brand = ensure_brand(item.brand)
        if not brand:
            continue
        key = brand.casefold()
        if key in seen_brands:
            continue
        seen_brands.add(key)
        normalized.append(
            {
                "domain": "",
                "website_url": "",
                "brand": brand,
                "aliases": [str(a).strip() for a in (item.aliases or []) if str(a).strip()],
                "summary": summary,
            }
        )
    return normalized


def _append_competitor(subject: Subject, row: dict[str, Any]) -> None:
    subject.competitors.append(
        Competitor(
            domain=row["domain"],
            website_url=row["website_url"],
            brand=row["brand"],
            aliases=row["aliases"],
            summary=row["summary"],
        )
    )


def _update_competitor(existing: Competitor, row: dict[str, Any]) -> None:
    existing.domain = row["domain"]
    existing.website_url = row["website_url"]
    existing.brand = row["brand"]
    existing.aliases = row["aliases"]
    existing.summary = row["summary"]


def apply_competitors(
    db: Session,
    subject: Subject,
    *,
    competitors: list[CompetitorItem],
) -> None:
    normalized: list[dict[str, Any]] = []
    for row in _normalize_competitor_items(competitors):
        normalized.append(row)
    assert_competitor_capacity(db, subject.tenant_id, subject, adding=len(normalized))
    for row in normalized:
        _append_competitor(subject, row)


def _existing_match_keys(subject: Subject) -> set[str]:
    keys: set[str] = set()
    for row in subject.competitors or []:
        key = competitor_match_key(domain=row.domain or "", brand=row.brand or "")
        if key is not None:
            keys.add(key)
    return keys


def add_competitor(
    db: Session,
    subject: Subject,
    *,
    item: CompetitorItem,
) -> Competitor:
    assert_competitor_capacity(db, subject.tenant_id, subject, adding=1)

    normalized = _normalize_competitor_items([item])
    if not normalized:
        raise InvalidCompetitorError("invalid competitor fields")

    row = normalized[0]
    key = competitor_match_key(domain=row["domain"], brand=row["brand"])
    if key is None or key in _existing_match_keys(subject):
        raise DuplicateCompetitorError("competitor already exists")

    _append_competitor(subject, row)
    db.flush()
    return subject.competitors[-1]


def update_competitor_by_id(
    db: Session,
    subject: Subject,
    *,
    competitor_id: UUID,
    item: CompetitorItem,
) -> Competitor:
    target: Competitor | None = None
    for row in subject.competitors or []:
        if row.id == competitor_id:
            target = row
            break
    if target is None:
        raise CompetitorNotFoundError("competitor not found")

    merged = CompetitorItem(
        domain=(item.domain or target.domain or "").strip(),
        website_url=(item.website_url or target.website_url or "").strip(),
        brand=(item.brand or target.brand or "").strip(),
        aliases=list(item.aliases if item.aliases is not None else (target.aliases or [])),
        summary=(item.summary if item.summary is not None else target.summary or "").strip(),
    )

    normalized = _normalize_competitor_items([merged])
    if not normalized:
        raise InvalidCompetitorError("invalid competitor fields")

    row = normalized[0]
    if competitor_match_key(domain=row["domain"], brand=row["brand"]) is None:
        raise InvalidCompetitorError("invalid competitor fields")

    if find_competitor_conflict(
        subject,
        domain=row["domain"],
        brand=row["brand"],
        exclude_competitor_id=competitor_id,
    ):
        raise DuplicateCompetitorError("competitor already exists")

    _update_competitor(target, row)
    db.flush()
    return target


def remove_competitor_by_id(
    db: Session,
    subject: Subject,
    *,
    competitor_id: UUID,
) -> UUID:
    target: Competitor | None = None
    for row in subject.competitors or []:
        if row.id == competitor_id:
            target = row
            break
    if target is None:
        raise CompetitorNotFoundError("competitor not found")

    removed_id = target.id
    if target in subject.competitors:
        subject.competitors.remove(target)
    db.delete(target)
    db.flush()
    return removed_id
