"""Brand report export audit and quota hooks."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from aperix_geo.db.models import BrandReportExport, User


def export_limit_for_tenant(_tenant_id: UUID) -> int | None:
    """Return max exports per billing period; None = unlimited (until membership wired)."""
    return None


def count_user_exports(
    db: Session,
    *,
    tenant_id: UUID,
    user_id: UUID,
    since: datetime | None = None,
) -> int:
    stmt = select(func.count(BrandReportExport.id)).where(
        BrandReportExport.tenant_id == tenant_id,
        BrandReportExport.user_id == user_id,
    )
    if since is not None:
        stmt = stmt.where(BrandReportExport.created_at >= since)
    return int(db.scalar(stmt) or 0)


def assert_export_allowed(db: Session, *, user: User) -> None:
    limit = export_limit_for_tenant(user.tenant_id)
    if limit is None:
        return
    used = count_user_exports(db, tenant_id=user.tenant_id, user_id=user.id)
    if used >= limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"导出次数已达上限（{limit} 次）",
        )


def record_brand_report_export(
    db: Session,
    *,
    user: User,
    subject_id: UUID,
    window_start: datetime,
    window_end: datetime,
    entity_id: str | None,
    platform: list[str] | None,
    topic_ids: list[UUID] | None,
    export_format: str = "pdf",
) -> BrandReportExport:
    row = BrandReportExport(
        tenant_id=user.tenant_id,
        subject_id=subject_id,
        user_id=user.id,
        window_start=window_start,
        window_end=window_end,
        entity_id=entity_id or "",
        platform=list(platform or []),
        topic_ids=[str(tid) for tid in (topic_ids or [])],
        format=export_format,
        created_at=datetime.now(UTC),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def export_usage_for_user(db: Session, *, user: User) -> dict[str, Any]:
    limit = export_limit_for_tenant(user.tenant_id)
    used = count_user_exports(db, tenant_id=user.tenant_id, user_id=user.id)
    return {
        "export_count": used,
        "export_limit": limit,
        "remaining": None if limit is None else max(0, limit - used),
    }
