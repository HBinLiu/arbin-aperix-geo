"""Public billing plan catalog API."""

from __future__ import annotations

from unittest.mock import patch

from fastapi.testclient import TestClient

from aperix_geo.main import app
from aperix_geo.services.billing.plan_catalog import (
    BillingCycleOption,
    PlanCatalog,
    PlanCatalogItem,
    PlanLimitDisplay,
    PlanPriceDisplay,
)


def _sample_catalog() -> PlanCatalog:
    return PlanCatalog(
        plans=(
            PlanCatalogItem(
                code="personal",
                name="个人版",
                description="适合个人或小团队。",
                orderable=True,
                limits=(
                    PlanLimitDisplay(
                        key="max_subjects",
                        label="品牌",
                        description="可创建与监测的品牌数量上限。",
                        value="1",
                    ),
                ),
                prices=(
                    PlanPriceDisplay(
                        billing_cycle="monthly",
                        monthly_cents=29900,
                        period_total_cents=29900,
                        discount_badge=None,
                    ),
                ),
            ),
        ),
        billing_cycles=(BillingCycleOption(id="monthly", label="月度", badge=None),),
    )


def test_plans_does_not_require_auth() -> None:
    catalog = _sample_catalog()
    with patch("aperix_geo.api.routes.billing.get_plan_catalog", return_value=catalog):
        client = TestClient(app)
        response = client.get("/api/v1/billing/plans")

    assert response.status_code == 200
    body = response.json()
    assert body["plans"][0]["code"] == "personal"
    assert body["plans"][0]["limits"][0]["value"] == "1"
    assert body["billing_cycles"][0]["id"] == "monthly"
