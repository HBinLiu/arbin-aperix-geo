"""Billing and subscription API schemas."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class PlanLimitItemOut(BaseModel):
    key: str
    label: str
    description: str
    value: str


class PlanPriceOut(BaseModel):
    billing_cycle: str
    monthly_cents: int | None = None
    period_total_cents: int | None = None
    discount_badge: str | None = None


class BillingCycleOptionOut(BaseModel):
    id: str
    label: str
    badge: str | None = None


class PlanCatalogItemOut(BaseModel):
    code: str
    name: str
    description: str
    orderable: bool
    limits: list[PlanLimitItemOut]
    prices: list[PlanPriceOut]


class PlanCatalogOut(BaseModel):
    plans: list[PlanCatalogItemOut]
    billing_cycles: list[BillingCycleOptionOut]


class UsagePackCatalogItemOut(BaseModel):
    code: str
    title: str
    order_label: str
    quantity: int
    price_cents: int
    unit_price_cents: int


class UsagePackCatalogOut(BaseModel):
    packs: list[UsagePackCatalogItemOut]


class PlanLimitsOut(BaseModel):
    max_subjects: int
    max_per_platforms: int
    max_per_competitors: int
    max_prompts_total: int
    per_month_usages: int
    sampling_frequency: str


class UsageOut(BaseModel):
    subjects_count: int
    prompts_count: int
    monthly_limit: int
    monthly_used: int
    monthly_remaining: int
    usage_pack_balance: int
    ai_requests_available: int


class SubscriptionOut(BaseModel):
    tenant_id: UUID
    plan_code: str
    plan_name: str
    billing_cycle: str
    status: str
    current_period_start: datetime
    current_period_end: datetime
    ai_period_start: datetime | None
    ai_period_end: datetime | None
    subscription_active: bool
    limits: PlanLimitsOut
    usage: UsageOut


class PaymentWebhookIn(BaseModel):
    order_id: UUID
    payment_id: str = Field(min_length=1, max_length=128)
    status: Literal["paid"] = "paid"


class PaymentWebhookOut(BaseModel):
    ok: bool = True
    order_id: UUID
    order_type: str
    status: str


class CreateSubscriptionOrderIn(BaseModel):
    plan_code: Literal["personal", "premium", "ultimate"]
    billing_cycle: Literal["monthly", "quarterly", "yearly"]


class CreateUsagePackOrderIn(BaseModel):
    product_code: Literal["pack_1000", "pack_5000", "pack_10000", "custom"]
    quantity: int | None = Field(default=None, ge=1)


class PayOrderOut(BaseModel):
    id: UUID
    order_type: str
    amount_cents: int
    status: str
    plan_code: str | None = None
    billing_cycle: str | None = None
    product_code: str | None = None
    quantity: int | None = None


class PayOrderListItemOut(BaseModel):
    id: UUID
    order_type: str
    amount_cents: int
    status: str
    created_at: datetime
    paid_at: datetime | None = None
    plan_code: str | None = None
    plan_name: str | None = None
    billing_cycle: str | None = None
    product_code: str | None = None
    product_label: str | None = None
    quantity: int | None = None


class PayOrderListOut(BaseModel):
    items: list[PayOrderListItemOut]
    total: int
    page: int
    page_size: int


class QuotaRecordListItemOut(BaseModel):
    id: UUID
    created_at: datetime
    record_type: str
    record_type_label: str
    source: str
    source_label: str
    amount_delta: int
    subject_id: UUID
    subject_brand: str


class QuotaRecordListOut(BaseModel):
    items: list[QuotaRecordListItemOut]
    total: int
    page: int
    page_size: int


class QuotaRecordTypeFilterOptionOut(BaseModel):
    value: str
    label: str


class QuotaRecordFiltersOut(BaseModel):
    days: list[int]
    record_types: list[QuotaRecordTypeFilterOptionOut]
    default_days: int
