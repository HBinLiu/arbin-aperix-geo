"""Subscription expiry and AI usage period rollover (Celery Beat)."""

from __future__ import annotations

import calendar
import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from aperix_geo.db.models import TenantSubscription, TenantUsagePeriod, ZERO_UUID
from aperix_geo.services.billing.quota import get_current_usage_period, get_limits_for_tenant, subscription_is_usable
from aperix_geo.services.billing.quota_ledger import record_subscription_grant

logger = logging.getLogger(__name__)

_MAX_CATCHUP_PERIODS = 24


def utc_now() -> datetime:
    return datetime.now(UTC)


def add_months(moment: datetime, months: int) -> datetime:
    """Advance by calendar months, clamping day-of-month."""
    month_index = moment.month - 1 + months
    year = moment.year + month_index // 12
    month = month_index % 12 + 1
    day = min(moment.day, calendar.monthrange(year, month)[1])
    return moment.replace(year=year, month=month, day=day)


def _latest_usage_period(db: Session, tenant_id: uuid.UUID) -> TenantUsagePeriod | None:
    return db.execute(
        select(TenantUsagePeriod)
        .where(
            TenantUsagePeriod.tenant_id == tenant_id,
            TenantUsagePeriod.deleted.is_(False),
        )
        .order_by(TenantUsagePeriod.period_start.desc())
        .limit(1)
    ).scalar_one_or_none()


def expire_due_subscriptions(db: Session, *, now: datetime | None = None) -> int:
    """Mark active/canceled subscriptions expired when billing period ends."""
    moment = now or utc_now()
    rows = db.execute(
        select(TenantSubscription)
        .where(
            TenantSubscription.deleted.is_(False),
            TenantSubscription.status.in_(("active", "canceled")),
            TenantSubscription.current_period_end <= moment,
        )
        .with_for_update(skip_locked=True)
    ).scalars().all()

    for sub in rows:
        if sub.pending_plan_id != ZERO_UUID:
            sub.plan_id = sub.pending_plan_id
            sub.pending_plan_id = ZERO_UUID
            logger.info(
                "账期末降级已生效 tenant=%s subscription=%s plan=%s",
                sub.tenant_id,
                sub.id,
                sub.plan_id,
            )
        sub.status = "expired"
        logger.info(
            "订阅已过期 tenant=%s subscription=%s ended=%s",
            sub.tenant_id,
            sub.id,
            sub.current_period_end.isoformat(),
        )
    return len(rows)


def _catch_up_usage_periods(db: Session, subscription: TenantSubscription, *, now: datetime) -> int:
    if not subscription_is_usable(subscription, now=now):
        return 0

    created = 0
    last = _latest_usage_period(db, subscription.tenant_id)

    if last is None:
        limits = get_limits_for_tenant(db, subscription.tenant_id)
        period_end = add_months(subscription.current_period_start, 1)
        if period_end > subscription.current_period_end:
            period_end = subscription.current_period_end
        if period_end <= now and period_end > subscription.current_period_start:
            period = TenantUsagePeriod(
                tenant_id=subscription.tenant_id,
                subscription_id=subscription.id,
                period_start=subscription.current_period_start,
                period_end=period_end,
                monthly_limit=limits.per_month_usages,
            )
            db.add(period)
            db.flush()
            record_subscription_grant(db, period=period, source="subscription")
            return 1
        return 0

    while created < _MAX_CATCHUP_PERIODS:
        if get_current_usage_period(db, subscription.tenant_id, now=now) is not None:
            break
        if last.period_end > now:
            break
        if not subscription_is_usable(subscription, now=last.period_end):
            break
        if last.period_end >= subscription.current_period_end:
            break

        limits = get_limits_for_tenant(db, subscription.tenant_id)
        new_start = last.period_end
        new_end = add_months(new_start, 1)
        if new_end > subscription.current_period_end:
            new_end = subscription.current_period_end
        if new_end <= new_start:
            break

        period = TenantUsagePeriod(
            tenant_id=subscription.tenant_id,
            subscription_id=subscription.id,
            period_start=new_start,
            period_end=new_end,
            monthly_limit=limits.per_month_usages,
        )
        db.add(period)
        db.flush()
        record_subscription_grant(db, period=period, source="rollover")
        last = period
        created += 1
        logger.info(
            "AI 用量周期已滚动 tenant=%s period=%s..%s limit=%d",
            subscription.tenant_id,
            new_start.isoformat(),
            new_end.isoformat(),
            limits.per_month_usages,
        )

    return created


def rollover_due_usage_periods(db: Session, *, now: datetime | None = None) -> int:
    """Create new AI usage periods for paid subscriptions whose current period ended."""
    moment = now or utc_now()
    subscriptions = db.execute(
        select(TenantSubscription)
        .where(
            TenantSubscription.deleted.is_(False),
            TenantSubscription.status.in_(("active", "canceled")),
            TenantSubscription.current_period_end > moment,
        )
    ).scalars().all()

    total = 0
    for sub in subscriptions:
        total += _catch_up_usage_periods(db, sub, now=moment)
    return total


def process_billing_maintenance(db: Session, *, now: datetime | None = None) -> dict[str, int]:
    """Expire subscriptions, roll AI usage periods, send quota warnings."""
    from aperix_geo.services.billing.warnings import process_quota_warnings

    expired = expire_due_subscriptions(db, now=now)
    rolled = rollover_due_usage_periods(db, now=now)
    warned = process_quota_warnings(db, now=now)
    db.commit()
    return {
        "expired_subscriptions": expired,
        "rolled_usage_periods": rolled,
        "quota_warnings_sent": warned,
    }
