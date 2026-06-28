"""Tests for payment order creation."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import pytest

from aperix_geo.db.models import Plan, PlanPack, PlanPrice, TenantPayOrder, TenantSubscription
from aperix_geo.services.billing.orders import (
    cancel_tenant_pay_order,
    create_subscription_order,
    create_usage_pack_order,
)


def _plan(**overrides: object) -> Plan:
    defaults = dict(
        id=uuid.uuid4(),
        code="premium",
        name="专业版",
        max_subjects=3,
        max_per_platforms=3,
        max_per_competitors=10,
        max_prompts_total=150,
        per_month_usages=8500,
        sampling_frequency="daily_1",
        is_active=True,
    )
    defaults.update(overrides)
    return Plan(**defaults)  # type: ignore[arg-type]


def test_create_subscription_order_new_tenant() -> None:
    plan = _plan()
    price = PlanPrice(
        id=uuid.uuid4(),
        plan_id=plan.id,
        billing_cycle="monthly",
        monthly_cents=89900,
        period_total_cents=89900,
    )
    db = MagicMock()
    db.execute.return_value.scalar_one_or_none.side_effect = [plan, price, None, None]

    order = create_subscription_order(
        db,
        tenant_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        plan_code="premium",
        billing_cycle="monthly",
    )

    assert order.order_type == "subscription"
    assert order.amount_cents == 89900
    assert order.status == "pending"
    db.add.assert_called_once()


def test_create_subscription_order_renewal() -> None:
    now = datetime(2026, 6, 15, tzinfo=UTC)
    plan = _plan()
    price = PlanPrice(
        id=uuid.uuid4(),
        plan_id=plan.id,
        billing_cycle="yearly",
        monthly_cents=71900,
        period_total_cents=862800,
    )
    subscription = TenantSubscription(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        plan_id=plan.id,
        billing_cycle="yearly",
        status="active",
        current_period_start=now - timedelta(days=30),
        current_period_end=now + timedelta(days=335),
    )
    db = MagicMock()
    db.execute.return_value.scalar_one_or_none.side_effect = [plan, price, None, subscription]

    order = create_subscription_order(
        db,
        tenant_id=subscription.tenant_id,
        user_id=uuid.uuid4(),
        plan_code="premium",
        billing_cycle="yearly",
    )

    assert order.order_type == "subscription_renewal"
    assert order.amount_cents == 862800


def test_create_subscription_order_plan_change() -> None:
    now = datetime(2026, 6, 15, tzinfo=UTC)
    current_plan = _plan(code="personal")
    target_plan = _plan(code="premium")
    price = PlanPrice(
        id=uuid.uuid4(),
        plan_id=target_plan.id,
        billing_cycle="monthly",
        monthly_cents=89900,
        period_total_cents=89900,
    )
    subscription = TenantSubscription(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        plan_id=current_plan.id,
        billing_cycle="monthly",
        status="active",
        current_period_start=now - timedelta(days=10),
        current_period_end=now + timedelta(days=20),
    )
    db = MagicMock()
    db.execute.return_value.scalar_one_or_none.side_effect = [target_plan, price, None, subscription]

    order = create_subscription_order(
        db,
        tenant_id=subscription.tenant_id,
        user_id=uuid.uuid4(),
        plan_code="premium",
        billing_cycle="monthly",
    )

    assert order.order_type == "plan_change"


def test_create_subscription_order_rejects_enterprise() -> None:
    plan = _plan(code="enterprise")
    db = MagicMock()
    db.execute.return_value.scalar_one_or_none.return_value = plan

    with pytest.raises(ValueError, match="self-service"):
        create_subscription_order(
            db,
            tenant_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            plan_code="enterprise",
            billing_cycle="monthly",
        )


def test_create_subscription_order_rejects_duplicate_pending() -> None:
    plan = _plan()
    price = PlanPrice(
        id=uuid.uuid4(),
        plan_id=plan.id,
        billing_cycle="monthly",
        monthly_cents=89900,
        period_total_cents=89900,
    )
    db = MagicMock()
    db.execute.return_value.scalar_one_or_none.side_effect = [plan, price, uuid.uuid4()]

    with pytest.raises(ValueError, match="pending order already exists"):
        create_subscription_order(
            db,
            tenant_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            plan_code="premium",
            billing_cycle="monthly",
        )


def test_create_usage_pack_order_fixed_pack() -> None:
    product = PlanPack(
        id=uuid.uuid4(),
        code="pack_1000",
        quantity=1000,
        price_cents=12900,
        unit_price_cents=13,
        min_quantity=100,
        is_active=True,
    )
    db = MagicMock()
    db.execute.return_value.scalar_one_or_none.side_effect = [None, product]

    order = create_usage_pack_order(
        db,
        tenant_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        product_code="pack_1000",
    )

    assert order.order_type == "usage_pack"
    assert order.amount_cents == 12900
    assert order.quantity == 1000


def test_create_usage_pack_order_custom() -> None:
    product = PlanPack(
        id=uuid.uuid4(),
        code="custom",
        quantity=0,
        price_cents=0,
        unit_price_cents=15,
        min_quantity=100,
        is_active=True,
    )
    db = MagicMock()
    db.execute.return_value.scalar_one_or_none.side_effect = [None, product]

    order = create_usage_pack_order(
        db,
        tenant_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        product_code="custom",
        quantity=200,
    )

    assert order.amount_cents == 3000
    assert order.quantity == 200


def test_cancel_tenant_pay_order_pending() -> None:
    tenant_id = uuid.uuid4()
    order = TenantPayOrder(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        user_id=uuid.uuid4(),
        order_type="usage_pack",
        amount_cents=12900,
        status="pending",
        product_code="pack_1000",
        quantity=1000,
        unit_price_cents=13,
    )
    db = MagicMock()
    db.execute.return_value.scalar_one_or_none.return_value = order

    canceled = cancel_tenant_pay_order(db, tenant_id=tenant_id, order_id=order.id)

    assert canceled.status == "canceled"


def test_cancel_tenant_pay_order_rejects_non_pending() -> None:
    tenant_id = uuid.uuid4()
    order = TenantPayOrder(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        user_id=uuid.uuid4(),
        order_type="usage_pack",
        amount_cents=12900,
        status="paid",
    )
    db = MagicMock()
    db.execute.return_value.scalar_one_or_none.return_value = order

    with pytest.raises(ValueError, match="Only pending orders can be canceled"):
        cancel_tenant_pay_order(db, tenant_id=tenant_id, order_id=order.id)
