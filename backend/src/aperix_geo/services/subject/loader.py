"""Load Subject rows with competitor relationships for sampling."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from aperix_geo.db.models import Subject


def load_subject_with_competitors(
    db: Session,
    subject_id: UUID,
    *,
    tenant_id: UUID | None = None,
) -> Subject | None:
    q = (
        select(Subject)
        .options(joinedload(Subject.competitors))
        .where(Subject.id == subject_id)
    )
    if tenant_id is not None:
        q = q.where(Subject.tenant_id == tenant_id)
    return db.execute(q).unique().scalar_one_or_none()


def competitor_lists(subject: Subject) -> tuple[list[str], list[str]]:
    """返回 (domains, brand_names) 供采样解析使用。"""
    domains: list[str] = []
    brands: list[str] = []
    for c in subject.competitors:
        domain = (c.domain or "").strip()
        brand = (c.brand or "").strip()
        if domain:
            domains.append(domain)
        if brand:
            brands.append(brand)
    return domains, brands
