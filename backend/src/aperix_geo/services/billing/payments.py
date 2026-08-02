"""Payment order fulfillment for subscriptions and usage packs."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from aperix_geo.db.models import EPOCH, Plan, PlanPack, Tenant, TenantPayOrder, TenantSubscription, TenantUsagePeriod, ZERO_UUID
from aperix_geo.services.billing.constants import BILLING_CYCLE_MONTHS, BILLING_CYCLES, SUBSCRIPTION_ORDER_TYPES
from aperix_geo.services.billing.quota import get_current_usage_period, get_limits_for_tenant, subscription_is_usable
from aperix_geo.services.billing.quota_ledger import record_pack_purchase, record_subscription_grant
from aperix_geo.services.billing.rollover import add_months

logger = logging.getLogger(__name__)


def utc_now() -> datetime:
    return datetime.now(UTC)


def _load_subscription(db: Session, tenant_id: uuid.UUID) -> TenantSubscription | None:
    return db.execute(
        select(TenantSubscription)
        .where(
            TenantSubscription.tenant_id == tenant_id,
            TenantSubscription.deleted.is_(False),
        )
        .limit(1)
    ).scalar_one_or_none()


def _load_order_for_update(db: Session, order_id: uuid.UUID) -> TenantPayOrder | None:
    return db.execute(
        select(TenantPayOrder)
        .where(
            TenantPayOrder.id == order_id,
            TenantPayOrder.deleted.is_(False),
        )
        .with_for_update()
    ).scalar_one_or_none()


def _billing_cycle_months(cycle: str) -> int:
    return BILLING_CYCLE_MONTHS.get(cycle, 1)


def _ensure_usage_period(db: Session, *, subscription: TenantSubscription, moment: datetime) -> None:
    if get_current_usage_period(db, subscription.tenant_id, now=moment) is not None:
        return
    limits = get_limits_for_tenant(db, subscription.tenant_id)
    period_start = subscription.current_period_start
    period_end = add_months(period_start, 1)
    if period_end > subscription.current_period_end:
        period_end = subscription.current_period_end
    db.add(
        TenantUsagePeriod(
            tenant_id=subscription.tenant_id,
            subscription_id=subscription.id,
            period_start=period_start,
            period_end=period_end,
            monthly_limit=limits.per_month_usages,
        )
    )
    db.flush()
    period = get_current_usage_period(db, subscription.tenant_id, now=moment)
    if period is not None:
        record_subscription_grant(db, period=period, source="subscription")


def _refresh_usage_period_limit(db: Session, *, tenant_id: uuid.UUID, moment: datetime) -> None:
    period = get_current_usage_period(db, tenant_id, now=moment)
    if period is None:
        return
    limits = get_limits_for_tenant(db, tenant_id)
    period.monthly_limit = limits.per_month_usages


def _apply_plan_change(
    db: Session,
    *,
    subscription: TenantSubscription,
    target_plan: Plan,
    moment: datetime,
) -> None:
    current_plan = db.get(Plan, subscription.plan_id)
    is_downgrade = (
        current_plan is not None
        and not current_plan.deleted
        and target_plan.sort_order < current_plan.sort_order
    )
    if is_downgrade:
        subscription.pending_plan_id = target_plan.id
        return

    subscription.plan_id = target_plan.id
    subscription.pending_plan_id = ZERO_UUID
    _refresh_usage_period_limit(db, tenant_id=subscription.tenant_id, moment=moment)


def _fulfill_subscription_order(
    db: Session,
    order: TenantPayOrder,
    *,
    paid_at: datetime,
) -> None:
    target_plan = db.get(Plan, order.plan_id)
    if target_plan is None or target_plan.deleted:
        raise ValueError("Plan not found for subscription order")

    subscription = _load_subscription(db, order.tenant_id)
    months = _billing_cycle_months(order.billing_cycle)
    moment = paid_at

    if subscription is None:
        period_start = moment
        period_end = add_months(moment, months)
        subscription = TenantSubscription(
            tenant_id=order.tenant_id,
            plan_id=order.plan_id,
            billing_cycle=order.billing_cycle,
            status="active",
            current_period_start=period_start,
            current_period_end=period_end,
        )
        db.add(subscription)
        db.flush()
    else:
        if subscription_is_usable(subscription, now=moment):
            period_start = subscription.current_period_start
            period_end = add_months(subscription.current_period_end, months)
        else:
            period_start = moment
            period_end = add_months(moment, months)

        if order.order_type == "plan_change":
            _apply_plan_change(
                db,
                subscription=subscription,
                target_plan=target_plan,
                moment=moment,
            )
        else:
            subscription.plan_id = order.plan_id
            subscription.pending_plan_id = ZERO_UUID

        subscription.billing_cycle = order.billing_cycle
        subscription.current_period_start = period_start
        subscription.current_period_end = period_end
        subscription.status = "active"
        subscription.canceled_at = EPOCH

    order.period_start = subscription.current_period_start
    order.period_end = subscription.current_period_end
    _ensure_usage_period(db, subscription=subscription, moment=moment)


def _fulfill_usage_pack_order(db: Session, order: TenantPayOrder) -> None:
    tenant = db.get(Tenant, order.tenant_id)
    if tenant is None or tenant.deleted:
        raise ValueError("Tenant not found for usage pack order")
    if order.quantity <= 0:
        raise ValueError("Usage pack quantity must be positive")

    product = db.execute(
        select(PlanPack)
        .where(
            PlanPack.code == order.product_code,
            PlanPack.deleted.is_(False),
            PlanPack.is_active.is_(True),
        )
        .limit(1)
    ).scalar_one_or_none()
    if product is None and order.product_code != "custom":
        raise ValueError("Usage pack product not found")

    tenant.usage_pack_balance += order.quantity


def assign_subscription_plan(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    plan_code: str,
    billing_cycle: str = "monthly",
    now: datetime | None = None,
) -> TenantSubscription:
    """Admin/dev helper: set tenant to a plan as if a subscription just completed."""
    cycle = billing_cycle.strip().lower()
    if cycle not in BILLING_CYCLES:
        raise ValueError(f"Unsupported billing_cycle: {billing_cycle}")

    plan = db.execute(
        select(Plan)
        .where(Plan.code == plan_code.strip().lower(), Plan.is_active.is_(True), Plan.deleted.is_(False))
        .limit(1)
    ).scalar_one_or_none()
    if plan is None:
        raise ValueError(f"Plan not found: {plan_code}")

    moment = now or utc_now()
    months = _billing_cycle_months(cycle)
    period_start = moment
    period_end = add_months(moment, months)

    subscription = _load_subscription(db, tenant_id)
    if subscription is None:
        subscription = TenantSubscription(
            tenant_id=tenant_id,
            plan_id=plan.id,
            billing_cycle=cycle,
            status="active",
            current_period_start=period_start,
            current_period_end=period_end,
        )
        db.add(subscription)
        db.flush()
    else:
        subscription.plan_id = plan.id
        subscription.pending_plan_id = ZERO_UUID
        subscription.billing_cycle = cycle
        subscription.status = "active"
        subscription.canceled_at = EPOCH
        subscription.current_period_start = period_start
        subscription.current_period_end = period_end

    _ensure_usage_period(db, subscription=subscription, moment=moment)
    _refresh_usage_period_limit(db, tenant_id=tenant_id, moment=moment)
    db.flush()
    logger.info(
        "已指派订阅 tenant=%s plan=%s cycle=%s period_end=%s",
        tenant_id,
        plan.code,
        cycle,
        period_end.isoformat(),
    )
    return subscription


def fulfill_paid_order(
    db: Session,
    order_id: uuid.UUID,
    *,
    payment_id: str,
    paid_at: datetime | None = None,
) -> TenantPayOrder:
    """Mark order paid and apply subscription / usage pack entitlements (idempotent)."""
    moment = paid_at or utc_now()
    order = _load_order_for_update(db, order_id)
    if order is None:
        raise ValueError("Order not found")

    if order.status == "paid":
        return order

    if order.status not in ("pending", "failed"):
        raise ValueError(f"Order status cannot transition to paid: {order.status}")

    if order.order_type in SUBSCRIPTION_ORDER_TYPES:
        _fulfill_subscription_order(db, order, paid_at=moment)
    elif order.order_type == "usage_pack":
        _fulfill_usage_pack_order(db, order)
    else:
        raise ValueError(f"Unsupported order type: {order.order_type}")

    order.status = "paid"
    order.payment_id = payment_id.strip()
    order.paid_at = moment
    if order.order_type == "usage_pack":
        record_pack_purchase(db, order)
    db.flush()
    logger.info(
        "支付订单已履约 order=%s tenant=%s type=%s payment_id=%s",
        order.id,
        order.tenant_id,
        order.order_type,
        order.payment_id,
    )
    return order
