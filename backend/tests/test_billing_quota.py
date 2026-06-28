"""Tests for billing quota service."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from aperix_geo.db.models import EPOCH, Plan, TenantPlanOverride, TenantSubscription, TenantUsagePeriod, ZERO_UUID
from aperix_geo.services.billing.exceptions import QuotaExceededError, SubscriptionInactiveError
from aperix_geo.services.billing.limits import PlanLimits, effective_int, effective_limits, effective_str
from aperix_geo.services.billing.quota import (
    assert_can_add_prompts,
    assert_can_create_subject,
    assert_competitor_capacity,
    assert_platform_capacity,
    consume_ai_usage,
    get_current_usage_period,
    subscription_is_usable,
)


def _record_consumption_side_effect(_db: MagicMock, **kwargs: object) -> MagicMock:
    row = MagicMock()
    row.consumed_from = kwargs["consumed_from"]
    return row


def _plan(**overrides: object) -> Plan:
    defaults = dict(
        id=uuid.uuid4(),
        code="personal",
        name="个人版",
        max_subjects=1,
        max_per_platforms=3,
        max_per_competitors=10,
        max_prompts_total=50,
        per_month_usages=2500,
        sampling_frequency="daily_1",
    )
    defaults.update(overrides)
    plan = Plan(**defaults)  # type: ignore[arg-type]
    return plan


def _override(**overrides: int | str) -> TenantPlanOverride:
    row = TenantPlanOverride(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        max_subjects=0,
        max_per_platforms=0,
        max_per_competitors=0,
        max_prompts_total=0,
        per_month_usages=0,
        sampling_frequency="",
    )
    for key, value in overrides.items():
        setattr(row, key, value)
    return row


def test_effective_int_and_str() -> None:
    assert effective_int(0, 5) == 5
    assert effective_int(10, 5) == 10
    assert effective_str("", "daily_1") == "daily_1"
    assert effective_str("weekly_1", "daily_1") == "weekly_1"


def test_effective_limits_without_override() -> None:
    plan = _plan()
    limits = effective_limits(plan, None)
    assert limits == PlanLimits(
        max_subjects=1,
        max_per_platforms=3,
        max_per_competitors=10,
        max_prompts_total=50,
        per_month_usages=2500,
        sampling_frequency="daily_1",
    )


def test_effective_limits_with_partial_override() -> None:
    plan = _plan()
    override = _override(max_subjects=5, per_month_usages=9000)
    limits = effective_limits(plan, override)
    assert limits.max_subjects == 5
    assert limits.max_per_platforms == 3
    assert limits.per_month_usages == 9000


def test_subscription_is_usable() -> None:
    now = datetime(2026, 6, 15, tzinfo=UTC)
    end = now + timedelta(days=10)
    active = TenantSubscription(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        plan_id=uuid.uuid4(),
        billing_cycle="monthly",
        status="active",
        current_period_start=now - timedelta(days=5),
        current_period_end=end,
    )
    canceled = TenantSubscription(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        plan_id=uuid.uuid4(),
        billing_cycle="monthly",
        status="canceled",
        current_period_start=now - timedelta(days=5),
        current_period_end=end,
        canceled_at=now,
    )
    expired = TenantSubscription(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        plan_id=uuid.uuid4(),
        billing_cycle="monthly",
        status="expired",
        current_period_start=now - timedelta(days=40),
        current_period_end=now - timedelta(days=10),
    )
    assert subscription_is_usable(active, now=now) is True
    assert subscription_is_usable(canceled, now=now) is True
    assert subscription_is_usable(expired, now=now) is False
    assert subscription_is_usable(active, now=end + timedelta(seconds=1)) is False


def test_get_current_usage_period_returns_active_row() -> None:
    tenant_id = uuid.uuid4()
    now = datetime(2026, 6, 15, 12, 0, tzinfo=UTC)
    period = TenantUsagePeriod(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        subscription_id=uuid.uuid4(),
        period_start=now - timedelta(days=1),
        period_end=now + timedelta(days=29),
        monthly_limit=2500,
        monthly_used=10,
    )
    db = MagicMock()
    db.execute.return_value.scalar_one_or_none.return_value = period
    assert get_current_usage_period(db, tenant_id, now=now) is period


def test_consume_ai_usage_uses_subscription_first() -> None:
    tenant_id = uuid.uuid4()
    now = datetime(2026, 6, 15, tzinfo=UTC)
    usage_period = TenantUsagePeriod(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        subscription_id=uuid.uuid4(),
        period_start=now - timedelta(days=1),
        period_end=now + timedelta(days=29),
        monthly_limit=2500,
        monthly_used=100,
    )

    db = MagicMock()

    with (
        patch("aperix_geo.services.billing.quota._advisory_lock_usage"),
        patch("aperix_geo.services.billing.quota.existing_consumption_pool", return_value=None),
        patch("aperix_geo.services.billing.quota.require_active_subscription"),
        patch("aperix_geo.services.billing.quota.get_current_usage_period", return_value=usage_period),
        patch("aperix_geo.services.billing.quota._atomic_increment_monthly_used", return_value=True) as mock_inc,
        patch("aperix_geo.services.billing.quota._atomic_decrement_pack_balance") as mock_pack,
        patch(
            "aperix_geo.services.billing.quota.record_consumption",
            side_effect=_record_consumption_side_effect,
        ) as mock_record,
    ):
        consumed = consume_ai_usage(
            db,
            tenant_id=tenant_id,
            source="sampling",
            subject_id=uuid.uuid4(),
            reference_id=uuid.uuid4(),
            now=now,
        )

    assert consumed == "subscription"
    mock_inc.assert_called_once_with(db, usage_period.id)
    mock_pack.assert_not_called()
    mock_record.assert_called_once()
    assert mock_record.call_args.kwargs["consumed_from"] == "subscription"
    assert mock_record.call_args.kwargs["source"] == "sampling"


def test_consume_ai_usage_uses_pack_when_monthly_exhausted() -> None:
    tenant_id = uuid.uuid4()
    now = datetime(2026, 6, 15, tzinfo=UTC)
    usage_period = TenantUsagePeriod(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        subscription_id=uuid.uuid4(),
        period_start=now - timedelta(days=1),
        period_end=now + timedelta(days=29),
        monthly_limit=2500,
        monthly_used=2500,
    )

    db = MagicMock()

    with (
        patch("aperix_geo.services.billing.quota._advisory_lock_usage"),
        patch("aperix_geo.services.billing.quota.existing_consumption_pool", return_value=None),
        patch("aperix_geo.services.billing.quota.require_active_subscription"),
        patch("aperix_geo.services.billing.quota.get_current_usage_period", return_value=usage_period),
        patch("aperix_geo.services.billing.quota._atomic_increment_monthly_used", return_value=False),
        patch("aperix_geo.services.billing.quota._atomic_decrement_pack_balance", return_value=True),
        patch(
            "aperix_geo.services.billing.quota.record_consumption",
            side_effect=_record_consumption_side_effect,
        ) as mock_record,
    ):
        consumed = consume_ai_usage(db, tenant_id=tenant_id, source="retry", now=now)

    assert consumed == "pack"
    assert mock_record.call_args.kwargs["consumed_from"] == "pack"


def test_consume_ai_usage_raises_when_exhausted() -> None:
    tenant_id = uuid.uuid4()
    now = datetime(2026, 6, 15, tzinfo=UTC)
    usage_period = TenantUsagePeriod(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        subscription_id=uuid.uuid4(),
        period_start=now - timedelta(days=1),
        period_end=now + timedelta(days=29),
        monthly_limit=2500,
        monthly_used=2500,
    )

    db = MagicMock()

    with (
        patch("aperix_geo.services.billing.quota._advisory_lock_usage"),
        patch("aperix_geo.services.billing.quota.existing_consumption_pool", return_value=None),
        patch("aperix_geo.services.billing.quota.require_active_subscription"),
        patch("aperix_geo.services.billing.quota.get_current_usage_period", return_value=usage_period),
        patch("aperix_geo.services.billing.quota._atomic_increment_monthly_used", return_value=False),
        patch("aperix_geo.services.billing.quota._atomic_decrement_pack_balance", return_value=False),
    ):
        with pytest.raises(QuotaExceededError):
            consume_ai_usage(db, tenant_id=tenant_id, source="parse", now=now)


def test_consume_ai_usage_uses_pack_without_active_period() -> None:
    tenant_id = uuid.uuid4()
    now = datetime(2026, 6, 15, tzinfo=UTC)

    db = MagicMock()

    with (
        patch("aperix_geo.services.billing.quota._advisory_lock_usage"),
        patch("aperix_geo.services.billing.quota.existing_consumption_pool", return_value=None),
        patch("aperix_geo.services.billing.quota.require_active_subscription"),
        patch("aperix_geo.services.billing.quota.get_current_usage_period", return_value=None),
        patch("aperix_geo.services.billing.quota._atomic_decrement_pack_balance", return_value=True) as mock_pack,
        patch(
            "aperix_geo.services.billing.quota.record_consumption",
            side_effect=_record_consumption_side_effect,
        ),
    ):
        consumed = consume_ai_usage(
            db,
            tenant_id=tenant_id,
            source="sampling",
            reference_id=uuid.uuid4(),
            now=now,
        )

    assert consumed == "pack"
    mock_pack.assert_called_once_with(db, tenant_id)


def test_consume_ai_usage_rejects_expired_subscription() -> None:
    tenant_id = uuid.uuid4()
    now = datetime(2026, 6, 15, tzinfo=UTC)
    subscription = TenantSubscription(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        plan_id=uuid.uuid4(),
        billing_cycle="monthly",
        status="expired",
        current_period_start=now - timedelta(days=40),
        current_period_end=now - timedelta(days=10),
    )

    db = MagicMock()

    def _execute(stmt: object) -> MagicMock:
        result = MagicMock()
        if "tb_tenant_subscriptions" in str(stmt):
            result.scalar_one_or_none.return_value = subscription
        return result

    db.execute.side_effect = _execute

    with (
        patch("aperix_geo.services.billing.quota._advisory_lock_usage"),
        patch("aperix_geo.services.billing.quota.existing_consumption_pool", return_value=None),
    ):
        with pytest.raises(SubscriptionInactiveError):
            consume_ai_usage(db, tenant_id=tenant_id, source="setup", now=now)


@patch("aperix_geo.services.billing.quota.get_limits_for_tenant")
@patch("aperix_geo.services.billing.quota.require_active_subscription")
@patch("aperix_geo.services.billing.quota._count_subjects", return_value=1)
def test_assert_can_create_subject_raises_at_limit(mock_count, _mock_sub, mock_limits) -> None:
    mock_limits.return_value = PlanLimits(
        max_subjects=1,
        max_per_platforms=3,
        max_per_competitors=10,
        max_prompts_total=50,
        per_month_usages=2500,
        sampling_frequency="daily_1",
    )
    db = MagicMock()
    with pytest.raises(QuotaExceededError) as exc:
        assert_can_create_subject(db, uuid.uuid4())
    assert exc.value.dimension == "max_subjects"


@patch("aperix_geo.services.billing.quota.get_limits_for_tenant")
@patch("aperix_geo.services.billing.quota.require_active_subscription")
def test_assert_platform_capacity_raises(_mock_sub, mock_limits) -> None:
    mock_limits.return_value = _plan(max_per_platforms=2)
    db = MagicMock()
    with pytest.raises(QuotaExceededError) as exc:
        assert_platform_capacity(db, uuid.uuid4(), 3)
    assert exc.value.dimension == "max_per_platforms"


@patch("aperix_geo.services.billing.quota.get_limits_for_tenant")
@patch("aperix_geo.services.billing.quota.require_active_subscription")
def test_assert_can_add_prompts_raises(_mock_sub, mock_limits) -> None:
    tenant_id = uuid.uuid4()
    mock_limits.return_value = PlanLimits(
        max_subjects=1,
        max_per_platforms=3,
        max_per_competitors=10,
        max_prompts_total=50,
        per_month_usages=2500,
        sampling_frequency="daily_1",
    )
    db = MagicMock()
    with patch("aperix_geo.services.billing.quota._count_prompts", return_value=50):
        with pytest.raises(QuotaExceededError) as exc:
            assert_can_add_prompts(db, tenant_id, count=1)
    assert exc.value.dimension == "max_prompts_total"
