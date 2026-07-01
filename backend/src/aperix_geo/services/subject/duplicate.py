"""租户内 Subject 唯一性校验（Setup 第一步验重）。"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from aperix_geo.db.models import Subject, SubjectType
from aperix_geo.services.brand.resolve import normalize_brand_key
from aperix_geo.utils.net import registrable_from


def find_tenant_subject_duplicate(
    db: Session,
    *,
    tenant_id: UUID,
    subject_type: SubjectType | str,
    domain: str = "",
    brand: str = "",
) -> Subject | None:
    """按租户 + 类型 + domain/brand 字段查找已存在的 subject（不含软删）。"""
    st = SubjectType(subject_type)
    if st == SubjectType.domain:
        domain_key = registrable_from(domain)
        if not domain_key:
            return None
        return db.execute(
            select(Subject)
            .where(
                Subject.tenant_id == tenant_id,
                Subject.type == SubjectType.domain,
                Subject.deleted.is_(False),
                Subject.domain == domain_key,
            )
            .limit(1)
        ).scalar_one_or_none()

    brand_key = normalize_brand_key(brand)
    if not brand_key:
        return None
    return db.execute(
        select(Subject)
        .where(
            Subject.tenant_id == tenant_id,
            Subject.type == SubjectType.brand,
            Subject.deleted.is_(False),
            func.lower(Subject.brand) == brand_key,
        )
        .limit(1)
    ).scalar_one_or_none()


def assert_tenant_subject_unique(
    db: Session,
    *,
    tenant_id: UUID,
    subject_type: SubjectType | str,
    domain: str = "",
    brand: str = "",
) -> None:
    """Setup 第一步：同租户下 domain/brand 监测主体不可重复创建。"""
    from aperix_geo.services.setup.exceptions import SubjectDuplicateError

    existing = find_tenant_subject_duplicate(
        db,
        tenant_id=tenant_id,
        subject_type=subject_type,
        domain=domain,
        brand=brand,
    )
    if existing is None:
        return
    st = SubjectType(subject_type)
    if st == SubjectType.domain:
        message = f"{existing.domain} 已是监测主体，请勿重复添加。"
    else:
        message = f"「{existing.brand}」已是监测主体，请勿重复添加。"
    raise SubjectDuplicateError(message, existing_subject_id=existing.id)
