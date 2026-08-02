"""Tests for billing quota service."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from aperix_geo.db.models import (
    EPOCH,
    LLMResponse,
    LLMResponseStatus,
    Plan,
    SamplingJob,
    Tenant,
    TenantPlanOverride,
    TenantSubscription,
    TenantUsagePeriod,
    ZERO_UUID,
)
from aperix_geo.services.billing.exceptions import QuotaExceededError, SubscriptionInactiveError
from aperix_geo.services.billing.limits import PlanLimits, effective_int, effective_limits, effective_str
from aperix_geo.services.billing.quota import (
    ai_usage_available,
    lock_tenant_ai_quota,
    assert_can_add_prompts,
    assert_can_create_subject,
    assert_competitor_capacity,
    assert_platform_capacity,
    assert_team_member_capacity,
    assert_subject_sampling_frequency,
    confirm_sampling_quota,
    consume_ai_usage,
    get_current_usage_period,
    release_sampling_quota,
    reserve_ai_usage,
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
        per_month_usages=2000,
        max_team_members=3,
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
        max_team_members=0,
        sampling_frequency="",
    )
    for key, value in overrides.items():
        setattr(row, key, value)
    return row


def test_effective_int_and_str() -> None:
    assert effective_int(0, 5) == 5
    assert effective_int(10, 5) == 10
    assert effective_str("", "daily_1") == "daily_1"
    assert effective_str("daily_7", "daily_1") == "daily_7"


def test_effective_limits_without_override() -> None:
    plan = _plan()
    limits = effective_limits(plan, None)
    assert limits == PlanLimits(
        max_subjects=1,
        max_per_platforms=3,
        max_per_competitors=10,
        max_prompts_total=50,
        per_month_usages=2000,
        max_team_members=3,
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


@patch("aperix_geo.services.billing.quota.get_limits_for_enforcement")
@patch("aperix_geo.services.billing.quota.is_first_subject_onboarding", return_value=False)
@patch("aperix_geo.services.billing.quota.require_active_subscription")
@patch("aperix_geo.services.billing.quota._count_subjects", return_value=1)
def test_assert_can_create_subject_raises_at_limit(
    mock_count, _mock_sub, _mock_onboarding, mock_limits
) -> None:
    mock_limits.return_value = PlanLimits(
        max_subjects=1,
        max_per_platforms=3,
        max_per_competitors=10,
        max_prompts_total=50,
        per_month_usages=2000,
        max_team_members=3,
        sampling_frequency="daily_1",
    )
    db = MagicMock()
    with pytest.raises(QuotaExceededError) as exc:
        assert_can_create_subject(db, uuid.uuid4())
    assert exc.value.dimension == "max_subjects"


@patch("aperix_geo.services.billing.quota.get_limits_for_enforcement")
@patch("aperix_geo.services.billing.quota.is_first_subject_onboarding", return_value=False)
@patch("aperix_geo.services.billing.quota.require_active_subscription")
def test_assert_platform_capacity_raises(_mock_sub, _mock_onboarding, mock_limits) -> None:
    mock_limits.return_value = _plan(max_per_platforms=2)
    db = MagicMock()
    with pytest.raises(QuotaExceededError) as exc:
        assert_platform_capacity(db, uuid.uuid4(), 3)
    assert exc.value.dimension == "max_per_platforms"


@patch("aperix_geo.services.billing.quota.get_limits_for_enforcement")
@patch("aperix_geo.services.billing.quota.is_first_subject_onboarding", return_value=False)
@patch("aperix_geo.services.billing.quota.require_active_subscription")
def test_assert_can_add_prompts_raises(_mock_sub, _mock_onboarding, mock_limits) -> None:
    tenant_id = uuid.uuid4()
    mock_limits.return_value = PlanLimits(
        max_subjects=1,
        max_per_platforms=3,
        max_per_competitors=10,
        max_prompts_total=50,
        per_month_usages=2000,
        max_team_members=3,
        sampling_frequency="daily_1",
    )
    db = MagicMock()
    with patch("aperix_geo.services.billing.quota._count_prompts", return_value=50):
        with pytest.raises(QuotaExceededError) as exc:
            assert_can_add_prompts(db, tenant_id, count=1)
    assert exc.value.dimension == "max_prompts_total"


@patch("aperix_geo.services.billing.quota.get_limits_for_tenant")
@patch("aperix_geo.services.billing.quota.require_active_subscription")
@patch("aperix_geo.services.billing.quota._count_tenant_members", return_value=3)
def test_assert_team_member_capacity_raises(_mock_count, _mock_sub, mock_limits) -> None:
    mock_limits.return_value = PlanLimits(
        max_subjects=1,
        max_per_platforms=3,
        max_per_competitors=10,
        max_prompts_total=50,
        per_month_usages=2000,
        max_team_members=3,
        sampling_frequency="daily_1",
    )
    db = MagicMock()
    with pytest.raises(QuotaExceededError) as exc:
        assert_team_member_capacity(db, uuid.uuid4(), adding=1)
    assert exc.value.dimension == "max_team_members"


@patch("aperix_geo.services.billing.quota.get_limits_for_tenant")
@patch("aperix_geo.services.billing.quota.require_active_subscription")
def test_assert_subject_sampling_frequency_rejects_invalid(_mock_sub, mock_limits) -> None:
    mock_limits.return_value = PlanLimits(
        max_subjects=1,
        max_per_platforms=3,
        max_per_competitors=10,
        max_prompts_total=50,
        per_month_usages=2000,
        max_team_members=3,
        sampling_frequency="daily_1",
    )
    db = MagicMock()
    with pytest.raises(QuotaExceededError) as exc:
        assert_subject_sampling_frequency(db, uuid.uuid4(), "hourly_1")
    assert exc.value.dimension == "sampling_frequency"


@patch("aperix_geo.services.billing.quota.get_limits_for_tenant")
@patch("aperix_geo.services.billing.quota.require_active_subscription")
def test_assert_subject_sampling_frequency_rejects_too_frequent(_mock_sub, mock_limits) -> None:
    mock_limits.return_value = PlanLimits(
        max_subjects=1,
        max_per_platforms=3,
        max_per_competitors=10,
        max_prompts_total=50,
        per_month_usages=2000,
        max_team_members=3,
        sampling_frequency="daily_7",
    )
    db = MagicMock()
    with pytest.raises(QuotaExceededError) as exc:
        assert_subject_sampling_frequency(db, uuid.uuid4(), "daily_1")
    assert exc.value.dimension == "sampling_frequency"


@patch("aperix_geo.services.billing.quota.get_limits_for_tenant")
@patch("aperix_geo.services.billing.quota.require_active_subscription")
def test_assert_subject_sampling_frequency_accepts_slower(_mock_sub, mock_limits) -> None:
    mock_limits.return_value = PlanLimits(
        max_subjects=1,
        max_per_platforms=3,
        max_per_competitors=10,
        max_prompts_total=50,
        per_month_usages=2000,
        max_team_members=3,
        sampling_frequency="daily_1",
    )
    db = MagicMock()
    assert assert_subject_sampling_frequency(db, uuid.uuid4(), "daily_3") == "daily_3"


def test_lock_tenant_ai_quota_locks_and_returns_available() -> None:
    tenant_id = uuid.uuid4()
    now = datetime(2026, 6, 15, tzinfo=UTC)
    tenant = Tenant(id=tenant_id, usage_pack_balance=5, usage_pack_reserved=1)
    period = TenantUsagePeriod(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        subscription_id=uuid.uuid4(),
        period_start=now - timedelta(days=1),
        period_end=now + timedelta(days=29),
        monthly_limit=100,
        monthly_used=10,
        monthly_reserved=20,
    )
    db = MagicMock()

    def _execute(stmt: object) -> MagicMock:
        result = MagicMock()
        sql = str(stmt)
        if "tb_tenants" in sql:
            result.scalar_one_or_none.return_value = tenant
        else:
            result.scalar_one.return_value = period
        return result

    db.execute.side_effect = _execute

    with (
        patch("aperix_geo.services.billing.quota.require_active_subscription"),
        patch("aperix_geo.services.billing.quota._advisory_lock_tenant_quota") as mock_lock,
        patch("aperix_geo.services.billing.quota.get_current_usage_period", return_value=period),
    ):
        assert lock_tenant_ai_quota(db, tenant_id, now=now) == 74  # 70 + 4

    mock_lock.assert_called_once_with(db, tenant_id)


def test_ai_usage_available_subtracts_reserved() -> None:
    tenant_id = uuid.uuid4()
    now = datetime(2026, 6, 15, tzinfo=UTC)
    tenant = Tenant(id=tenant_id, usage_pack_balance=5, usage_pack_reserved=2)
    period = TenantUsagePeriod(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        subscription_id=uuid.uuid4(),
        period_start=now - timedelta(days=1),
        period_end=now + timedelta(days=29),
        monthly_limit=100,
        monthly_used=10,
        monthly_reserved=20,
    )
    db = MagicMock()
    db.get.return_value = tenant

    with (
        patch("aperix_geo.services.billing.quota.require_active_subscription"),
        patch("aperix_geo.services.billing.quota.get_current_usage_period", return_value=period),
    ):
        # monthly free 70 + pack free 3
        assert ai_usage_available(db, tenant_id, now=now) == 73


def test_reserve_ai_usage_prefers_monthly_then_pack() -> None:
    tenant_id = uuid.uuid4()
    now = datetime(2026, 6, 15, tzinfo=UTC)
    tenant = Tenant(id=tenant_id, usage_pack_balance=10, usage_pack_reserved=0)
    period = TenantUsagePeriod(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        subscription_id=uuid.uuid4(),
        period_start=now - timedelta(days=1),
        period_end=now + timedelta(days=29),
        monthly_limit=100,
        monthly_used=95,
        monthly_reserved=0,
    )
    job = SamplingJob(id=uuid.uuid4(), tenant_id=tenant_id, subject_id=uuid.uuid4())
    db = MagicMock()

    def _execute(stmt: object) -> MagicMock:
        result = MagicMock()
        sql = str(stmt)
        if "tb_tenants" in sql:
            result.scalar_one_or_none.return_value = tenant
            result.scalar_one.return_value = tenant
        else:
            result.scalar_one.return_value = period
        return result

    db.execute.side_effect = _execute

    with (
        patch("aperix_geo.services.billing.quota.require_active_subscription"),
        patch("aperix_geo.services.billing.quota._advisory_lock_tenant_quota"),
        patch("aperix_geo.services.billing.quota.get_current_usage_period", return_value=period),
    ):
        reserve_ai_usage(db, tenant_id=tenant_id, amount=8, job=job, now=now)

    assert period.monthly_reserved == 5
    assert tenant.usage_pack_reserved == 3
    assert job.quota_usage_period_id == period.id
    assert job.quota_reserved_monthly == 5
    assert job.quota_reserved_pack == 3
    assert job.quota_open_monthly == 5
    assert job.quota_open_pack == 3


def test_reserve_ai_usage_is_additive_on_retry_top_up() -> None:
    tenant_id = uuid.uuid4()
    now = datetime(2026, 6, 15, tzinfo=UTC)
    tenant = Tenant(id=tenant_id, usage_pack_balance=10, usage_pack_reserved=0)
    period = TenantUsagePeriod(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        subscription_id=uuid.uuid4(),
        period_start=now - timedelta(days=1),
        period_end=now + timedelta(days=29),
        monthly_limit=100,
        monthly_used=0,
        monthly_reserved=2,
    )
    job = SamplingJob(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        subject_id=uuid.uuid4(),
        quota_usage_period_id=period.id,
        quota_reserved_monthly=2,
        quota_open_monthly=2,
        quota_reserved_pack=0,
        quota_open_pack=0,
    )
    db = MagicMock()

    def _execute(stmt: object) -> MagicMock:
        result = MagicMock()
        sql = str(stmt)
        if "tb_tenants" in sql:
            result.scalar_one_or_none.return_value = tenant
            result.scalar_one.return_value = tenant
        else:
            result.scalar_one.return_value = period
        return result

    db.execute.side_effect = _execute

    with (
        patch("aperix_geo.services.billing.quota.require_active_subscription"),
        patch("aperix_geo.services.billing.quota._advisory_lock_tenant_quota"),
        patch("aperix_geo.services.billing.quota.get_current_usage_period", return_value=period),
    ):
        reserve_ai_usage(db, tenant_id=tenant_id, amount=3, job=job, now=now)

    assert period.monthly_reserved == 5
    assert job.quota_reserved_monthly == 5
    assert job.quota_open_monthly == 5
    assert job.quota_usage_period_id == period.id


def test_reserve_ai_usage_raises_when_insufficient() -> None:
    tenant_id = uuid.uuid4()
    now = datetime(2026, 6, 15, tzinfo=UTC)
    tenant = Tenant(id=tenant_id, usage_pack_balance=1, usage_pack_reserved=0)
    period = TenantUsagePeriod(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        subscription_id=uuid.uuid4(),
        period_start=now - timedelta(days=1),
        period_end=now + timedelta(days=29),
        monthly_limit=10,
        monthly_used=10,
        monthly_reserved=0,
    )
    job = SamplingJob(id=uuid.uuid4(), tenant_id=tenant_id, subject_id=uuid.uuid4())
    db = MagicMock()

    def _execute(stmt: object) -> MagicMock:
        result = MagicMock()
        sql = str(stmt)
        if "tb_tenants" in sql:
            result.scalar_one_or_none.return_value = tenant
            result.scalar_one.return_value = tenant
        else:
            result.scalar_one.return_value = period
        return result

    db.execute.side_effect = _execute

    with (
        patch("aperix_geo.services.billing.quota.require_active_subscription"),
        patch("aperix_geo.services.billing.quota._advisory_lock_tenant_quota"),
        patch("aperix_geo.services.billing.quota.get_current_usage_period", return_value=period),
        pytest.raises(QuotaExceededError, match="额度不足"),
    ):
        reserve_ai_usage(db, tenant_id=tenant_id, amount=5, job=job, now=now)


def test_confirm_and_release_sampling_quota_are_idempotent() -> None:
    tenant_id = uuid.uuid4()
    now = datetime(2026, 6, 15, tzinfo=UTC)
    tenant = Tenant(id=tenant_id, usage_pack_balance=0, usage_pack_reserved=0)
    period = TenantUsagePeriod(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        subscription_id=uuid.uuid4(),
        period_start=now - timedelta(days=1),
        period_end=now + timedelta(days=29),
        monthly_limit=100,
        monthly_used=0,
        monthly_reserved=2,
    )
    job = SamplingJob(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        subject_id=uuid.uuid4(),
        quota_usage_period_id=period.id,
        quota_reserved_monthly=2,
        quota_reserved_pack=0,
        quota_open_monthly=2,
        quota_open_pack=0,
    )
    row_ok = LLMResponse(
        id=uuid.uuid4(),
        sampling_job_id=job.id,
        prompt_id=uuid.uuid4(),
        platform="doubao",
        status=LLMResponseStatus.pending,
        quota_settled=False,
    )
    row_fail = LLMResponse(
        id=uuid.uuid4(),
        sampling_job_id=job.id,
        prompt_id=uuid.uuid4(),
        platform="doubao",
        status=LLMResponseStatus.pending,
        quota_settled=False,
    )
    db = MagicMock()

    def _execute(stmt: object) -> MagicMock:
        result = MagicMock()
        sql = str(stmt)
        if "tb_sampling_jobs" in sql:
            result.scalar_one.return_value = job
        elif "tb_tenants" in sql:
            result.scalar_one.return_value = tenant
        elif "tb_tenant_usage_periods" in sql:
            result.scalar_one_or_none.return_value = period
            result.scalar_one.return_value = period
        else:
            result.scalar_one.return_value = period
        return result

    db.execute.side_effect = _execute

    with (
        patch("aperix_geo.services.billing.quota._advisory_lock_tenant_quota"),
        patch("aperix_geo.services.billing.quota.existing_consumption_pool", return_value=None),
        patch(
            "aperix_geo.services.billing.quota.record_consumption",
            side_effect=_record_consumption_side_effect,
        ),
    ):
        assert confirm_sampling_quota(db, job=job, row=row_ok, now=now) == "subscription"
        assert row_ok.quota_settled is True
        assert period.monthly_used == 1
        assert period.monthly_reserved == 1
        assert job.quota_open_monthly == 1

        # Idempotent confirm
        assert confirm_sampling_quota(db, job=job, row=row_ok, now=now) == ""
        assert period.monthly_used == 1

        release_sampling_quota(db, job=job, row=row_fail)
        assert row_fail.quota_settled is True
        assert period.monthly_reserved == 0
        assert job.quota_open_monthly == 0

        release_sampling_quota(db, job=job, row=row_fail)
        assert period.monthly_reserved == 0


def test_confirm_sampling_quota_uses_bound_period_not_current() -> None:
    tenant_id = uuid.uuid4()
    now = datetime(2026, 6, 15, tzinfo=UTC)
    tenant = Tenant(id=tenant_id, usage_pack_balance=0, usage_pack_reserved=0)
    reserved_period = TenantUsagePeriod(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        subscription_id=uuid.uuid4(),
        period_start=now - timedelta(days=40),
        period_end=now - timedelta(days=10),
        monthly_limit=100,
        monthly_used=0,
        monthly_reserved=1,
    )
    current_period = TenantUsagePeriod(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        subscription_id=uuid.uuid4(),
        period_start=now - timedelta(days=1),
        period_end=now + timedelta(days=29),
        monthly_limit=100,
        monthly_used=0,
        monthly_reserved=0,
    )
    job = SamplingJob(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        subject_id=uuid.uuid4(),
        quota_usage_period_id=reserved_period.id,
        quota_reserved_monthly=1,
        quota_open_monthly=1,
    )
    row = LLMResponse(
        id=uuid.uuid4(),
        sampling_job_id=job.id,
        prompt_id=uuid.uuid4(),
        platform="doubao",
        status=LLMResponseStatus.pending,
        quota_settled=False,
    )
    db = MagicMock()

    def _execute(stmt: object) -> MagicMock:
        result = MagicMock()
        sql = str(stmt)
        if "tb_sampling_jobs" in sql:
            result.scalar_one.return_value = job
        elif "tb_tenants" in sql:
            result.scalar_one.return_value = tenant
        else:
            result.scalar_one_or_none.return_value = reserved_period
        return result

    db.execute.side_effect = _execute

    with (
        patch("aperix_geo.services.billing.quota._advisory_lock_tenant_quota"),
        patch(
            "aperix_geo.services.billing.quota.get_current_usage_period",
            return_value=current_period,
        ),
        patch("aperix_geo.services.billing.quota.existing_consumption_pool", return_value=None),
        patch(
            "aperix_geo.services.billing.quota.record_consumption",
            side_effect=_record_consumption_side_effect,
        ),
    ):
        assert confirm_sampling_quota(db, job=job, row=row, now=now) == "subscription"

    assert reserved_period.monthly_used == 1
    assert reserved_period.monthly_reserved == 0
    assert current_period.monthly_used == 0
    assert current_period.monthly_reserved == 0


def test_delete_sampling_jobs_releases_open_quota() -> None:
    job_id = uuid.uuid4()
    job = SamplingJob(
        id=job_id,
        tenant_id=uuid.uuid4(),
        subject_id=uuid.uuid4(),
        quota_open_monthly=3,
    )
    db = MagicMock()
    lock_result = MagicMock()
    lock_result.scalar_one_or_none.return_value = job
    delete_result = MagicMock()
    delete_result.rowcount = 1
    db.execute.side_effect = [lock_result, delete_result]

    from aperix_geo.services.billing.quota import delete_sampling_jobs_releasing_quota

    with patch(
        "aperix_geo.services.billing.quota.release_remaining_job_quota",
        return_value=3,
    ) as mock_release:
        deleted = delete_sampling_jobs_releasing_quota(db, [job_id])

    assert deleted == 1
    mock_release.assert_called_once_with(db, job=job)
