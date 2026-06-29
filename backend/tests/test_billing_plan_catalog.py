"""Tests for subscription plan catalog."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock

from aperix_geo.db.models import Plan, PlanPrice
from aperix_geo.services.billing.plan_catalog import get_plan_catalog


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
        is_active=True,
        sort_order=1,
        deleted=False,
    )
    defaults.update(overrides)
    plan = Plan(**defaults)  # type: ignore[arg-type]
    plan.prices = overrides.get("prices", [])  # type: ignore[assignment]
    return plan


def test_get_plan_catalog_formats_limits_and_prices() -> None:
    personal = _plan(
        prices=[
            PlanPrice(
                id=uuid.uuid4(),
                plan_id=uuid.uuid4(),
                billing_cycle="monthly",
                monthly_cents=29900,
                period_total_cents=29900,
                discount_label="",
                deleted=False,
            ),
            PlanPrice(
                id=uuid.uuid4(),
                plan_id=uuid.uuid4(),
                billing_cycle="quarterly",
                monthly_cents=26900,
                period_total_cents=80700,
                discount_label="-10%",
                deleted=False,
            ),
        ]
    )
    enterprise = _plan(
        code="enterprise",
        name="企业版",
        max_subjects=999999,
        max_per_platforms=999999,
        max_per_competitors=999999,
        max_prompts_total=999999,
        per_month_usages=999999,
        max_team_members=999999,
        sort_order=4,
        prices=[
            PlanPrice(
                id=uuid.uuid4(),
                plan_id=uuid.uuid4(),
                billing_cycle="monthly",
                monthly_cents=0,
                period_total_cents=0,
                discount_label="",
                deleted=False,
            )
        ],
    )

    db = MagicMock()
    db.execute.return_value.scalars.return_value.all.return_value = [personal, enterprise]

    catalog = get_plan_catalog(db)

    assert len(catalog.plans) == 2
    assert catalog.plans[0].orderable is True
    assert catalog.plans[0].limits[0].value == "1"
    limits_by_key = {limit.key: limit for limit in catalog.plans[0].limits}
    assert limits_by_key["sampling_frequency"].value == "每天 / 每3天 / 每周"
    assert limits_by_key["sampling_frequency"].comparison_only is True
    assert limits_by_key["max_per_competitors"].value == "最多10"
    assert limits_by_key["per_month_usages"].value == "2,000 / 月"
    assert limits_by_key["max_team_members"].value == "最多3"
    assert catalog.plans[0].prices[1].monthly_cents == 26900
    assert catalog.plans[0].prices[1].discount_badge == "省 10%"

    assert catalog.plans[1].orderable is False
    assert all(limit.value == "自定义" for limit in catalog.plans[1].limits)
    assert catalog.plans[1].prices[0].monthly_cents is None

    assert [cycle.id for cycle in catalog.billing_cycles] == ["monthly", "quarterly"]
    assert catalog.billing_cycles[1].badge == "省 10%"
