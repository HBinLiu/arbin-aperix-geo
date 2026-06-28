"""Unified tenant quota ledger writes."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from aperix_geo.db.models import TenantPayOrder, TenantQuotaLedger, TenantUsagePeriod, ZERO_UUID
from aperix_geo.services.billing.constants import (
    LEDGER_RECORD_CONSUMPTION,
    LEDGER_RECORD_SUBSCRIPTION_GRANT,
    LEDGER_RECORD_USAGE_PACK_PURCHASE,
)

# Re-export for callers that import record type constants from here.
RECORD_TYPE_CONSUMPTION = LEDGER_RECORD_CONSUMPTION
RECORD_TYPE_USAGE_PACK_PURCHASE = LEDGER_RECORD_USAGE_PACK_PURCHASE
RECORD_TYPE_SUBSCRIPTION_GRANT = LEDGER_RECORD_SUBSCRIPTION_GRANT


def _find_existing_ledger_row(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    record_type: str,
    reference_id: uuid.UUID,
    source: str,
) -> TenantQuotaLedger | None:
    if reference_id == ZERO_UUID:
        return None
    return db.execute(
        select(TenantQuotaLedger).where(
            TenantQuotaLedger.tenant_id == tenant_id,
            TenantQuotaLedger.record_type == record_type,
            TenantQuotaLedger.reference_id == reference_id,
            TenantQuotaLedger.source == source,
            TenantQuotaLedger.deleted.is_(False),
        ).limit(1)
    ).scalar_one_or_none()


def append_quota_ledger_entry(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    record_type: str,
    amount_delta: int,
    source: str,
    reference_id: uuid.UUID = ZERO_UUID,
    consumed_from: str = "",
    subject_id: uuid.UUID = ZERO_UUID,
    platform: str = "",
    input_tokens: int = 0,
    output_tokens: int = 0,
    total_tokens: int = 0,
    created_at: datetime | None = None,
) -> TenantQuotaLedger | None:
    existing = _find_existing_ledger_row(
        db,
        tenant_id=tenant_id,
        record_type=record_type,
        reference_id=reference_id,
        source=source,
    )
    if existing is not None:
        return existing

    row_kwargs: dict = {
        "tenant_id": tenant_id,
        "record_type": record_type,
        "amount_delta": amount_delta,
        "source": source,
        "reference_id": reference_id,
        "consumed_from": consumed_from,
        "subject_id": subject_id,
        "platform": platform,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
    }
    if created_at is not None:
        row_kwargs["created_at"] = created_at
        row_kwargs["updated_at"] = created_at

    row = TenantQuotaLedger(**row_kwargs)
    db.add(row)
    try:
        db.flush()
    except IntegrityError:
        replay = _find_existing_ledger_row(
            db,
            tenant_id=tenant_id,
            record_type=record_type,
            reference_id=reference_id,
            source=source,
        )
        if replay is not None:
            return replay
        raise
    return row


def record_subscription_grant(
    db: Session,
    *,
    period: TenantUsagePeriod,
    source: str = "subscription",
) -> TenantQuotaLedger | None:
    return append_quota_ledger_entry(
        db,
        tenant_id=period.tenant_id,
        record_type=LEDGER_RECORD_SUBSCRIPTION_GRANT,
        amount_delta=period.monthly_limit,
        source=source,
        reference_id=period.id,
        consumed_from="",
        created_at=period.period_start,
    )


def record_pack_purchase(db: Session, order: TenantPayOrder) -> TenantQuotaLedger | None:
    return append_quota_ledger_entry(
        db,
        tenant_id=order.tenant_id,
        record_type=LEDGER_RECORD_USAGE_PACK_PURCHASE,
        amount_delta=order.quantity,
        source="usage_pack",
        reference_id=order.id,
        consumed_from="",
        created_at=order.paid_at,
    )


def record_consumption(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    source: str,
    consumed_from: str,
    reference_id: uuid.UUID = ZERO_UUID,
    subject_id: uuid.UUID = ZERO_UUID,
    platform: str = "",
    input_tokens: int = 0,
    output_tokens: int = 0,
    total_tokens: int = 0,
) -> TenantQuotaLedger | None:
    return append_quota_ledger_entry(
        db,
        tenant_id=tenant_id,
        record_type=LEDGER_RECORD_CONSUMPTION,
        amount_delta=-1,
        source=source,
        reference_id=reference_id,
        consumed_from=consumed_from,
        subject_id=subject_id,
        platform=platform.strip(),
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total_tokens,
    )


def existing_consumption_pool(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    reference_id: uuid.UUID,
    source: str,
) -> str | None:
    if reference_id == ZERO_UUID:
        return None
    return db.execute(
        select(TenantQuotaLedger.consumed_from).where(
            TenantQuotaLedger.tenant_id == tenant_id,
            TenantQuotaLedger.record_type == LEDGER_RECORD_CONSUMPTION,
            TenantQuotaLedger.reference_id == reference_id,
            TenantQuotaLedger.source == source,
            TenantQuotaLedger.deleted.is_(False),
        ).limit(1)
    ).scalar_one_or_none()
