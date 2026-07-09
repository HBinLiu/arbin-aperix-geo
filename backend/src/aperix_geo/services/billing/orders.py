"""Create pending payment orders for subscriptions and usage packs."""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from aperix_geo.db.models import Plan, PlanPack, PlanPrice, TenantPayOrder, TenantSubscription
from aperix_geo.services.billing.constants import (
    BILLING_CYCLES,
    CUSTOM_USAGE_PACK_CODE,
    ORDERABLE_PLAN_CODES,
    SUBSCRIPTION_ORDER_TYPES,
    USAGE_PACK_ORDER_TYPE,
)
from aperix_geo.services.billing.pagination import normalize_pagination
from aperix_geo.services.billing.quota import subscription_is_usable


def _assert_no_pending_order(db: Session, tenant_id: uuid.UUID, *, order_types: frozenset[str]) -> None:
    existing = db.execute(
        select(TenantPayOrder.id)
        .where(
            TenantPayOrder.tenant_id == tenant_id,
            TenantPayOrder.status == "pending",
            TenantPayOrder.order_type.in_(order_types),
            TenantPayOrder.deleted.is_(False),
        )
        .limit(1)
    ).scalar_one_or_none()
    if existing is not None:
        raise ValueError("A pending order already exists for this tenant")


def _load_plan_by_code(db: Session, plan_code: str) -> Plan:
    plan = db.execute(
        select(Plan).where(Plan.code == plan_code, Plan.is_active.is_(True)).limit(1)
    ).scalar_one_or_none()
    if plan is None:
        raise ValueError(f"Plan not found: {plan_code}")
    if plan.code not in ORDERABLE_PLAN_CODES:
        raise ValueError("Plan is not available for self-service purchase")
    return plan


def _load_plan_price(db: Session, *, plan_id: uuid.UUID, billing_cycle: str) -> PlanPrice:
    if billing_cycle not in BILLING_CYCLES:
        raise ValueError(f"Invalid billing cycle: {billing_cycle}")
    price = db.execute(
        select(PlanPrice)
        .where(PlanPrice.plan_id == plan_id, PlanPrice.billing_cycle == billing_cycle)
        .limit(1)
    ).scalar_one_or_none()
    if price is None:
        raise ValueError("Plan price not configured")
    if price.period_total_cents <= 0:
        raise ValueError("Plan is not available for self-service purchase")
    return price


def _load_subscription(db: Session, tenant_id: uuid.UUID) -> TenantSubscription | None:
    return db.execute(
        select(TenantSubscription)
        .where(
            TenantSubscription.tenant_id == tenant_id,
            TenantSubscription.deleted.is_(False),
        )
        .limit(1)
    ).scalar_one_or_none()


def _resolve_subscription_order_type(
    subscription: TenantSubscription | None,
    target_plan_id: uuid.UUID,
) -> str:
    if subscription is None or not subscription_is_usable(subscription):
        return "subscription"
    if subscription.plan_id == target_plan_id:
        return "subscription_renewal"
    return "plan_change"


def create_subscription_order(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    plan_code: str,
    billing_cycle: str,
) -> TenantPayOrder:
    """Create a pending subscription / renewal / plan-change order."""
    plan = _load_plan_by_code(db, plan_code)
    price = _load_plan_price(db, plan_id=plan.id, billing_cycle=billing_cycle)
    _assert_no_pending_order(db, tenant_id, order_types=SUBSCRIPTION_ORDER_TYPES)
    subscription = _load_subscription(db, tenant_id)
    order_type = _resolve_subscription_order_type(subscription, plan.id)

    order = TenantPayOrder(
        tenant_id=tenant_id,
        user_id=user_id,
        order_type=order_type,
        amount_cents=price.period_total_cents,
        status="pending",
        plan_id=plan.id,
        billing_cycle=billing_cycle,
    )
    db.add(order)
    db.flush()
    return order


_PAY_ORDER_SORT_COLUMNS = {
    "created_at": TenantPayOrder.created_at,
    "amount_cents": TenantPayOrder.amount_cents,
    "status": TenantPayOrder.status,
    "paid_at": TenantPayOrder.paid_at,
}


def list_tenant_pay_orders_paginated(
    db: Session,
    tenant_id: uuid.UUID,
    *,
    page: int = 1,
    page_size: int = 10,
    sort_by: str = "created_at",
    order: str = "desc",
) -> tuple[list[TenantPayOrder], int, int, int]:
    safe_page, safe_page_size = normalize_pagination(page, page_size)
    sort_column = _PAY_ORDER_SORT_COLUMNS.get(sort_by, TenantPayOrder.created_at)
    ordering = sort_column.asc() if order == "asc" else sort_column.desc()

    count_stmt = select(func.count()).select_from(TenantPayOrder).where(
        TenantPayOrder.tenant_id == tenant_id,
        TenantPayOrder.deleted.is_(False),
    )
    total = int(db.execute(count_stmt).scalar_one())

    offset = (safe_page - 1) * safe_page_size
    orders = list(
        db.execute(
            select(TenantPayOrder)
            .where(
                TenantPayOrder.tenant_id == tenant_id,
                TenantPayOrder.deleted.is_(False),
            )
            .order_by(ordering)
            .offset(offset)
            .limit(safe_page_size)
        )
        .scalars()
        .all()
    )
    return orders, total, safe_page, safe_page_size


def get_pay_order_by_id(db: Session, order_id: uuid.UUID, *, for_update: bool = False) -> TenantPayOrder:
    stmt = select(TenantPayOrder).where(
        TenantPayOrder.id == order_id,
        TenantPayOrder.deleted.is_(False),
    )
    if for_update:
        stmt = stmt.with_for_update()
    order = db.execute(stmt).scalar_one_or_none()
    if order is None:
        raise ValueError("Order not found")
    return order


def get_tenant_pay_order(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    order_id: uuid.UUID,
) -> TenantPayOrder:
    order = db.execute(
        select(TenantPayOrder).where(
            TenantPayOrder.id == order_id,
            TenantPayOrder.tenant_id == tenant_id,
            TenantPayOrder.deleted.is_(False),
        )
    ).scalar_one_or_none()
    if order is None:
        raise ValueError("Order not found")
    return order


def cancel_tenant_pay_order(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    order_id: uuid.UUID,
) -> TenantPayOrder:
    """Cancel a pending payment order for the tenant."""
    order = db.execute(
        select(TenantPayOrder)
        .where(
            TenantPayOrder.id == order_id,
            TenantPayOrder.tenant_id == tenant_id,
            TenantPayOrder.deleted.is_(False),
        )
        .with_for_update()
    ).scalar_one_or_none()
    if order is None:
        raise ValueError("Order not found")
    if order.status != "pending":
        raise ValueError("Only pending orders can be canceled")
    order.status = "canceled"
    db.flush()
    return order


def create_usage_pack_order(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    product_code: str,
    quantity: int | None = None,
) -> TenantPayOrder:
    """Create a pending AI usage pack order."""
    _assert_no_pending_order(db, tenant_id, order_types=frozenset({USAGE_PACK_ORDER_TYPE}))
    product = db.execute(
        select(PlanPack)
        .where(
            PlanPack.code == product_code,
            PlanPack.deleted.is_(False),
            PlanPack.is_active.is_(True),
        )
        .limit(1)
    ).scalar_one_or_none()
    if product is None:
        raise ValueError("Usage pack product not found")

    if product_code == CUSTOM_USAGE_PACK_CODE:
        if quantity is None or quantity < product.min_quantity:
            raise ValueError(f"Custom quantity must be at least {product.min_quantity}")
        pack_quantity = quantity
        unit_price = product.unit_price_cents
        amount = pack_quantity * unit_price
    else:
        if product.quantity <= 0 or product.price_cents <= 0:
            raise ValueError("Invalid usage pack product configuration")
        if quantity is not None and quantity != product.quantity:
            raise ValueError("Fixed pack quantity cannot be overridden")
        pack_quantity = product.quantity
        unit_price = product.unit_price_cents
        amount = product.price_cents

    order = TenantPayOrder(
        tenant_id=tenant_id,
        user_id=user_id,
        order_type=USAGE_PACK_ORDER_TYPE,
        amount_cents=amount,
        status="pending",
        product_code=product_code,
        quantity=pack_quantity,
        unit_price_cents=unit_price,
    )
    db.add(order)
    db.flush()
    return order
