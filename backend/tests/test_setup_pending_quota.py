"""Tests for first-subject setup deferred AI billing."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from aperix_geo.db.models import EPOCH, Plan, Tenant, TenantQuotaLedger, TenantSubscription, TenantUsagePeriod
from aperix_geo.services.billing.constants import LEDGER_RECORD_PENDING_SETUP
from aperix_geo.services.billing.exceptions import QuotaExceededError, SubscriptionInactiveError
from aperix_geo.services.billing.quota import (
    assert_setup_ai_usage_available,
    charge_setup_ai_usage,
    get_subscription_snapshot,
    settle_pending_setup_usage,
)


def _personal_plan() -> Plan:
    return Plan(
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


def test_get_subscription_snapshot_without_subscription_is_inactive() -> None:
    tenant_id = uuid.uuid4()
    tenant = Tenant(id=tenant_id, name="Acme", usage_pack_balance=0, usage_pack_reserved=0)
    plan = _personal_plan()
    db = MagicMock()
    db.get.return_value = tenant

    with (
        patch("aperix_geo.services.billing.quota._find_subscription", return_value=None),
        patch("aperix_geo.services.billing.quota.personal_plan_limits") as mock_limits,
        patch("aperix_geo.services.billing.quota._count_subjects", return_value=1),
        patch("aperix_geo.services.billing.quota._count_prompts", return_value=3),
    ):
        mock_limits.return_value = MagicMock(
            max_subjects=1,
            max_per_platforms=3,
            max_per_competitors=10,
            max_prompts_total=50,
            per_month_usages=2000,
            max_team_members=3,
            sampling_frequency="daily_1",
        )
        db.execute.return_value.scalar_one.return_value = plan
        snap = get_subscription_snapshot(db, tenant_id)

    assert snap.subscription_active is False
    assert snap.status == "expired"
    assert snap.plan_code == "personal"
    assert snap.current_period_start == EPOCH
    assert snap.usage.ai_requests_available == 0


def test_charge_setup_ai_usage_defers_during_onboarding() -> None:
    tenant_id = uuid.uuid4()
    ref = uuid.uuid4()
    db = MagicMock()

    with (
        patch("aperix_geo.services.billing.quota.tenant_has_usable_subscription", return_value=False),
        patch("aperix_geo.services.billing.quota.is_first_subject_onboarding", return_value=True),
        patch("aperix_geo.services.billing.quota.existing_pending_setup_usage", return_value=None),
        patch("aperix_geo.services.billing.quota.count_pending_setup_usage", return_value=0),
        patch("aperix_geo.services.billing.quota.record_pending_setup_usage") as mock_pending,
        patch("aperix_geo.services.billing.quota.consume_ai_usage") as mock_consume,
    ):
        out = charge_setup_ai_usage(
            db,
            tenant_id=tenant_id,
            reference_id=ref,
            platform="deepseek",
            usage={"input_tokens": 1, "output_tokens": 2, "total_tokens": 3},
        )

    assert out == "pending"
    mock_pending.assert_called_once()
    mock_consume.assert_not_called()


def test_charge_setup_ai_usage_consumes_when_subscribed() -> None:
    tenant_id = uuid.uuid4()
    ref = uuid.uuid4()
    db = MagicMock()

    with (
        patch("aperix_geo.services.billing.quota.tenant_has_usable_subscription", return_value=True),
        patch("aperix_geo.services.billing.quota.consume_ai_usage", return_value="subscription") as mock_consume,
        patch("aperix_geo.services.billing.quota.record_pending_setup_usage") as mock_pending,
    ):
        out = charge_setup_ai_usage(db, tenant_id=tenant_id, reference_id=ref, usage={})

    assert out == "subscription"
    mock_consume.assert_called_once()
    mock_pending.assert_not_called()


def test_assert_setup_ai_rejects_when_not_onboarding() -> None:
    db = MagicMock()
    with (
        patch("aperix_geo.services.billing.quota.tenant_has_usable_subscription", return_value=False),
        patch("aperix_geo.services.billing.quota.is_first_subject_onboarding", return_value=False),
        pytest.raises(SubscriptionInactiveError),
    ):
        assert_setup_ai_usage_available(db, uuid.uuid4())


def test_settle_pending_setup_usage_consumes_and_soft_deletes() -> None:
    tenant_id = uuid.uuid4()
    now = datetime(2026, 6, 15, tzinfo=UTC)
    pending = TenantQuotaLedger(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        record_type=LEDGER_RECORD_PENDING_SETUP,
        amount_delta=-1,
        source="setup",
        reference_id=uuid.uuid4(),
        platform="deepseek",
        input_tokens=1,
        output_tokens=2,
        total_tokens=3,
    )
    db = MagicMock()

    with (
        patch("aperix_geo.services.billing.quota.require_active_subscription"),
        patch("aperix_geo.services.billing.quota.list_pending_setup_usage", return_value=[pending]),
        patch("aperix_geo.services.billing.quota.consume_ai_usage", return_value="subscription") as mock_consume,
    ):
        settled = settle_pending_setup_usage(db, tenant_id, now=now)

    assert settled == 1
    assert pending.deleted is True
    mock_consume.assert_called_once()
    assert mock_consume.call_args.kwargs["reference_id"] == pending.reference_id


def test_assert_setup_ai_soft_cap() -> None:
    db = MagicMock()
    with (
        patch("aperix_geo.services.billing.quota.tenant_has_usable_subscription", return_value=False),
        patch("aperix_geo.services.billing.quota.is_first_subject_onboarding", return_value=True),
        patch("aperix_geo.services.billing.quota.count_pending_setup_usage", return_value=50),
        pytest.raises(QuotaExceededError, match="设置向导"),
    ):
        assert_setup_ai_usage_available(db, uuid.uuid4())
