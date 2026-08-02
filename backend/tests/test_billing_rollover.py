"""Tests for billing subscription rollover."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

from aperix_geo.db.models import Plan, TenantSubscription, TenantUsagePeriod, ZERO_UUID
from aperix_geo.services.billing.limits import PlanLimits
from aperix_geo.services.billing.rollover import (
    add_months,
    expire_due_subscriptions,
    process_billing_maintenance,
    rollover_due_usage_periods,
)


def test_add_months_clamps_day() -> None:
    start = datetime(2026, 1, 31, 12, 0, tzinfo=UTC)
    assert add_months(start, 1) == datetime(2026, 2, 28, 12, 0, tzinfo=UTC)


def test_expire_due_subscriptions_marks_expired() -> None:
    now = datetime(2026, 6, 15, tzinfo=UTC)
    sub = TenantSubscription(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        plan_id=uuid.uuid4(),
        billing_cycle="monthly",
        status="active",
        current_period_start=now - timedelta(days=40),
        current_period_end=now - timedelta(days=1),
    )
    db = MagicMock()
    exec_result = MagicMock()
    exec_result.scalars.return_value.all.return_value = [sub]
    exec_result.rowcount = 1
    db.execute.return_value = exec_result

    count = expire_due_subscriptions(db, now=now)

    assert count == 1
    assert sub.status == "expired"
    assert db.execute.call_count >= 2


def test_expire_due_subscriptions_applies_pending_plan() -> None:
    now = datetime(2026, 6, 15, tzinfo=UTC)
    pending_plan_id = uuid.uuid4()
    sub = TenantSubscription(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        plan_id=uuid.uuid4(),
        pending_plan_id=pending_plan_id,
        billing_cycle="monthly",
        status="active",
        current_period_start=now - timedelta(days=40),
        current_period_end=now - timedelta(days=1),
    )
    db = MagicMock()
    db.execute.return_value.scalars.return_value.all.return_value = [sub]

    count = expire_due_subscriptions(db, now=now)

    assert count == 1
    assert sub.plan_id == pending_plan_id
    assert sub.pending_plan_id == ZERO_UUID
    assert sub.status == "expired"


def test_rollover_creates_next_usage_period() -> None:
    now = datetime(2026, 6, 15, tzinfo=UTC)
    tenant_id = uuid.uuid4()
    sub = TenantSubscription(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        plan_id=uuid.uuid4(),
        billing_cycle="monthly",
        status="active",
        current_period_start=now - timedelta(days=45),
        current_period_end=now + timedelta(days=15),
    )
    last_period = TenantUsagePeriod(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        subscription_id=sub.id,
        period_start=now - timedelta(days=45),
        period_end=now - timedelta(days=15),
        monthly_limit=2000,
        monthly_used=900,
    )
    db = MagicMock()
    db.execute.return_value.scalars.return_value.all.return_value = [sub]

    with (
        patch("aperix_geo.services.billing.rollover.get_current_usage_period", return_value=None),
        patch("aperix_geo.services.billing.rollover._latest_usage_period", return_value=last_period),
        patch(
            "aperix_geo.services.billing.rollover.get_limits_for_tenant",
            return_value=PlanLimits(
                max_subjects=1,
                max_per_platforms=3,
                max_per_competitors=10,
                max_prompts_total=50,
                per_month_usages=2000,
                max_team_members=3,
                sampling_frequency="daily_1",
            ),
        ),
    ):
        created = rollover_due_usage_periods(db, now=now)

    assert created == 1
    db.add.assert_called_once()
    period = db.add.call_args[0][0]
    assert period.period_start == last_period.period_end
    assert period.monthly_limit == 2000


def test_process_billing_maintenance_commits() -> None:
    db = MagicMock()
    with (
        patch("aperix_geo.services.billing.rollover.expire_due_subscriptions", return_value=2),
        patch("aperix_geo.services.billing.rollover.rollover_due_usage_periods", return_value=3),
        patch("aperix_geo.services.billing.warnings.process_quota_warnings", return_value=1),
    ):
        result = process_billing_maintenance(db, now=datetime(2026, 6, 15, tzinfo=UTC))

    assert result == {
        "expired_subscriptions": 2,
        "rolled_usage_periods": 3,
        "quota_warnings_sent": 1,
    }
    db.commit.assert_called_once()
