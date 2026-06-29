"""Tests for payment order fulfillment."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from aperix_geo.db.models import EPOCH, Plan, Tenant, TenantPayOrder, TenantSubscription, TenantUsagePeriod, ZERO_UUID
from aperix_geo.services.billing.payments import fulfill_paid_order


def _plan(**overrides: object) -> Plan:
    defaults = dict(
        id=uuid.uuid4(),
        code="personal",
        name="个人版",
        max_subjects=1,
        max_per_platforms=3,
        max_per_competitors=10,
        max_prompts_total=50,
        per_month_usages=2000,
        max_team_members=3,
        sampling_frequency="daily_1",
        sort_order=1,
    )
    defaults.update(overrides)
    return Plan(**defaults)  # type: ignore[arg-type]


def _mock_order_db(order: TenantPayOrder, *, get_map: dict | None = None) -> MagicMock:
    db = MagicMock()
    db.execute.return_value.scalar_one_or_none.return_value = order
    mapping = {order.id: order, **(get_map or {})}
    db.get.side_effect = lambda model, pk: mapping.get(pk)
    return db


def test_fulfill_usage_pack_increments_balance() -> None:
    tenant_id = uuid.uuid4()
    tenant = Tenant(id=tenant_id, name="Acme", usage_pack_balance=100)
    order = TenantPayOrder(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        order_type="usage_pack",
        amount_cents=12900,
        status="pending",
        product_code="pack_1000",
        quantity=1000,
        unit_price_cents=13,
    )

    db = _mock_order_db(order, get_map={tenant_id: tenant})
    db.execute.return_value.scalar_one_or_none.side_effect = [order, None]

    with pytest.raises(ValueError, match="Usage pack product not found"):
        fulfill_paid_order(db, order.id, payment_id="pay-1")

    product = MagicMock(deleted=False, is_active=True)
    db.execute.return_value.scalar_one_or_none.side_effect = [order, product, None]

    with patch("aperix_geo.services.billing.payments.record_pack_purchase"):
        paid = fulfill_paid_order(db, order.id, payment_id="pay-1")

    assert paid.status == "paid"
    assert tenant.usage_pack_balance == 1100


def test_fulfill_subscription_is_idempotent_when_already_paid() -> None:
    order_id = uuid.uuid4()
    order = TenantPayOrder(
        id=order_id,
        tenant_id=uuid.uuid4(),
        order_type="subscription",
        amount_cents=29900,
        status="paid",
        plan_id=uuid.uuid4(),
        billing_cycle="monthly",
    )
    db = _mock_order_db(order)

    result = fulfill_paid_order(db, order_id, payment_id="pay-duplicate")

    assert result is order
    db.add.assert_not_called()


def test_fulfill_subscription_reactivates_expired() -> None:
    now = datetime(2026, 6, 15, tzinfo=UTC)
    tenant_id = uuid.uuid4()
    plan = _plan()
    subscription = TenantSubscription(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        plan_id=plan.id,
        billing_cycle="monthly",
        status="expired",
        current_period_start=now - timedelta(days=60),
        current_period_end=now - timedelta(days=30),
    )
    order = TenantPayOrder(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        order_type="subscription_renewal",
        amount_cents=29900,
        status="pending",
        plan_id=plan.id,
        billing_cycle="monthly",
    )

    db = _mock_order_db(order, get_map={plan.id: plan})
    db.execute.return_value.scalar_one_or_none.side_effect = [order, subscription]

    with (
        patch("aperix_geo.services.billing.payments.get_current_usage_period", return_value=None),
        patch(
            "aperix_geo.services.billing.payments.get_limits_for_tenant",
            return_value=MagicMock(per_month_usages=2000),
        ),
    ):
        paid = fulfill_paid_order(db, order.id, payment_id="pay-renew", paid_at=now)

    assert paid.status == "paid"
    assert subscription.status == "active"
    assert subscription.current_period_end > now


def test_fulfill_plan_change_upgrade_updates_plan_and_limit() -> None:
    now = datetime(2026, 6, 15, tzinfo=UTC)
    tenant_id = uuid.uuid4()
    personal = _plan(code="personal", sort_order=1, per_month_usages=2000)
    premium = _plan(code="premium", sort_order=2, per_month_usages=7000)
    subscription = TenantSubscription(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        plan_id=personal.id,
        billing_cycle="monthly",
        status="active",
        current_period_start=now - timedelta(days=10),
        current_period_end=now + timedelta(days=20),
    )
    usage_period = TenantUsagePeriod(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        subscription_id=subscription.id,
        period_start=now - timedelta(days=10),
        period_end=now + timedelta(days=20),
        monthly_limit=2000,
        monthly_used=100,
    )
    order = TenantPayOrder(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        order_type="plan_change",
        amount_cents=89900,
        status="pending",
        plan_id=premium.id,
        billing_cycle="monthly",
    )

    db = _mock_order_db(order, get_map={premium.id: premium, personal.id: personal})
    db.execute.return_value.scalar_one_or_none.side_effect = [order, subscription]

    limits = MagicMock(per_month_usages=7000)
    with (
        patch("aperix_geo.services.billing.payments.get_current_usage_period", return_value=usage_period),
        patch("aperix_geo.services.billing.payments.get_limits_for_tenant", return_value=limits),
    ):
        fulfill_paid_order(db, order.id, payment_id="pay-upgrade", paid_at=now)

    assert subscription.plan_id == premium.id
    assert subscription.pending_plan_id == ZERO_UUID
    assert usage_period.monthly_limit == 7000


def test_fulfill_plan_change_downgrade_sets_pending_plan() -> None:
    now = datetime(2026, 6, 15, tzinfo=UTC)
    tenant_id = uuid.uuid4()
    personal = _plan(code="personal", sort_order=1)
    premium = _plan(code="premium", sort_order=2)
    subscription = TenantSubscription(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        plan_id=premium.id,
        billing_cycle="monthly",
        status="active",
        current_period_start=now - timedelta(days=10),
        current_period_end=now + timedelta(days=20),
    )
    order = TenantPayOrder(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        order_type="plan_change",
        amount_cents=29900,
        status="pending",
        plan_id=personal.id,
        billing_cycle="monthly",
    )

    db = _mock_order_db(order, get_map={personal.id: personal, premium.id: premium})
    db.execute.return_value.scalar_one_or_none.side_effect = [order, subscription]

    with (
        patch("aperix_geo.services.billing.payments.get_current_usage_period", return_value=None),
        patch(
            "aperix_geo.services.billing.payments.get_limits_for_tenant",
            return_value=MagicMock(per_month_usages=7000),
        ),
    ):
        fulfill_paid_order(db, order.id, payment_id="pay-downgrade", paid_at=now)

    assert subscription.plan_id == premium.id
    assert subscription.pending_plan_id == personal.id
