"""Paginated tenant quota ledger listing and export."""

from __future__ import annotations

import csv
import io
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from aperix_geo.db.models import Subject, TenantPayOrder, TenantQuotaLedger, ZERO_UUID
from aperix_geo.services.billing.constants import (
    LEDGER_RECORD_USAGE_PACK_PURCHASE,
    QUOTA_RECORD_ALLOWED_DAYS,
    QUOTA_RECORD_DEFAULT_DAYS,
    QUOTA_RECORD_MAX_EXPORT_ROWS,
)
from aperix_geo.services.billing.ledger import (
    api_record_type_and_label,
    ledger_api_record_type_clauses,
    ledger_source_label,
    normalize_api_record_type_filter,
    quota_record_type_filter_options,
)
from aperix_geo.services.billing.pagination import normalize_pagination

_LEDGER_SORT_COLUMNS = {
    "created_at": TenantQuotaLedger.created_at,
    "source": TenantQuotaLedger.source,
    "amount_delta": TenantQuotaLedger.amount_delta,
}


@dataclass(frozen=True)
class QuotaRecordFiltersMeta:
    days: list[int]
    record_types: list[tuple[str, str]]
    default_days: int


def quota_record_filter_options() -> QuotaRecordFiltersMeta:
    return QuotaRecordFiltersMeta(
        days=sorted(QUOTA_RECORD_ALLOWED_DAYS),
        record_types=quota_record_type_filter_options(),
        default_days=QUOTA_RECORD_DEFAULT_DAYS,
    )


@dataclass(frozen=True)
class QuotaRecordRow:
    id: uuid.UUID
    created_at: datetime
    record_type: str
    record_type_label: str
    source: str
    source_label: str
    amount_delta: int
    subject_id: uuid.UUID
    subject_brand: str


def _normalize_days(days: int | None) -> int | None:
    if days is None:
        return None
    return days if days in QUOTA_RECORD_ALLOWED_DAYS else None


def _since_from_days(days: int | None) -> datetime | None:
    safe_days = _normalize_days(days)
    if safe_days is None:
        return None
    return datetime.now(UTC) - timedelta(days=safe_days)


def _ledger_filters(
    tenant_id: uuid.UUID,
    *,
    days: int | None = None,
    record_type: str | None = None,
) -> list:
    clauses = [
        TenantQuotaLedger.tenant_id == tenant_id,
        TenantQuotaLedger.deleted.is_(False),
    ]
    since = _since_from_days(days)
    if since is not None:
        clauses.append(TenantQuotaLedger.created_at >= since)
    safe_record_type = normalize_api_record_type_filter(record_type)
    if safe_record_type is not None:
        clauses.extend(ledger_api_record_type_clauses(safe_record_type))
    return clauses


def _ledger_base_query(
    tenant_id: uuid.UUID,
    *,
    days: int | None = None,
    record_type: str | None = None,
) -> Select:
    return (
        select(
            TenantQuotaLedger,
            func.coalesce(Subject.brand, "").label("subject_brand"),
            TenantPayOrder.product_code,
            TenantPayOrder.quantity,
        )
        .outerjoin(
            Subject,
            (TenantQuotaLedger.subject_id == Subject.id) & (TenantQuotaLedger.subject_id != ZERO_UUID),
        )
        .outerjoin(
            TenantPayOrder,
            (TenantQuotaLedger.reference_id == TenantPayOrder.id)
            & (TenantQuotaLedger.record_type == LEDGER_RECORD_USAGE_PACK_PURCHASE),
        )
        .where(*_ledger_filters(tenant_id, days=days, record_type=record_type))
    )


def _row_to_quota_record(
    ledger: TenantQuotaLedger,
    subject_brand: str,
    product_code: str | None,
    product_quantity: int | None,
) -> QuotaRecordRow:
    api_type, api_label = api_record_type_and_label(
        record_type=ledger.record_type,
        consumed_from=ledger.consumed_from,
    )
    return QuotaRecordRow(
        id=ledger.id,
        created_at=ledger.created_at,
        record_type=api_type,
        record_type_label=api_label,
        source=ledger.source,
        source_label=ledger_source_label(
            record_type=ledger.record_type,
            source=ledger.source,
            product_code=product_code or "",
            product_quantity=int(product_quantity or ledger.amount_delta or 0),
        ),
        amount_delta=ledger.amount_delta,
        subject_id=ledger.subject_id,
        subject_brand=subject_brand or "",
    )


def _fetch_quota_records(
    db: Session,
    tenant_id: uuid.UUID,
    *,
    days: int | None = None,
    record_type: str | None = None,
    sort_by: str = "created_at",
    order: str = "desc",
    limit: int | None = None,
    offset: int = 0,
) -> list[QuotaRecordRow]:
    sort_column = _LEDGER_SORT_COLUMNS.get(sort_by, TenantQuotaLedger.created_at)
    ordering = sort_column.asc() if order == "asc" else sort_column.desc()
    stmt = _ledger_base_query(tenant_id, days=days, record_type=record_type).order_by(ordering).offset(offset)
    if limit is not None:
        stmt = stmt.limit(limit)
    rows = db.execute(stmt).all()
    return [
        _row_to_quota_record(ledger, subject_brand, product_code, product_quantity)
        for ledger, subject_brand, product_code, product_quantity in rows
    ]


def list_tenant_quota_records_paginated(
    db: Session,
    tenant_id: uuid.UUID,
    *,
    page: int = 1,
    page_size: int = 10,
    sort_by: str = "created_at",
    order: str = "desc",
    days: int | None = None,
    record_type: str | None = None,
) -> tuple[list[QuotaRecordRow], int, int, int]:
    safe_page, safe_page_size = normalize_pagination(page, page_size)

    count_stmt = select(func.count()).select_from(TenantQuotaLedger).where(
        *_ledger_filters(tenant_id, days=days, record_type=record_type),
    )
    total = int(db.execute(count_stmt).scalar_one())

    offset = (safe_page - 1) * safe_page_size
    items = _fetch_quota_records(
        db,
        tenant_id,
        days=days,
        record_type=record_type,
        sort_by=sort_by,
        order=order,
        limit=safe_page_size,
        offset=offset,
    )
    return items, total, safe_page, safe_page_size


def export_tenant_quota_records_csv(
    db: Session,
    tenant_id: uuid.UUID,
    *,
    sort_by: str = "created_at",
    order: str = "desc",
    days: int | None = None,
    record_type: str | None = None,
) -> str:
    rows = _fetch_quota_records(
        db,
        tenant_id,
        days=days,
        record_type=record_type,
        sort_by=sort_by,
        order=order,
        limit=QUOTA_RECORD_MAX_EXPORT_ROWS,
    )
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["时间", "品牌", "类型", "来源", "变动额度"])
    for row in rows:
        writer.writerow(
            [
                row.created_at.astimezone(UTC).strftime("%Y-%m-%d %H:%M:%S"),
                row.subject_brand or "—",
                row.record_type_label,
                row.source_label,
                f"+{row.amount_delta}" if row.amount_delta > 0 else str(row.amount_delta),
            ]
        )
    return "\ufeff" + buffer.getvalue()