"""Shared billing domain constants."""

from __future__ import annotations

BILLING_CYCLES: tuple[str, ...] = ("monthly", "quarterly", "yearly")
BILLING_CYCLE_MONTHS: dict[str, int] = {
    "monthly": 1,
    "quarterly": 3,
    "yearly": 12,
}

ORDERABLE_PLAN_CODES: frozenset[str] = frozenset({"personal", "premium", "ultimate"})
ENTERPRISE_PLAN_CODE = "enterprise"
CUSTOM_USAGE_PACK_CODE = "custom"

SUBSCRIPTION_ORDER_TYPES: frozenset[str] = frozenset(
    {"subscription", "subscription_renewal", "plan_change"}
)
USAGE_PACK_ORDER_TYPE = "usage_pack"

CUSTOM_LIMIT_THRESHOLD = 999_999

API_PAGE_SIZE_MAX = 50

# Quota ledger DB record_type values
LEDGER_RECORD_CONSUMPTION = "consumption"
LEDGER_RECORD_USAGE_PACK_PURCHASE = "usage_pack_purchase"
LEDGER_RECORD_SUBSCRIPTION_GRANT = "subscription_grant"

# API-facing record type filters / list items
API_RECORD_SUBSCRIPTION_CONSUME = "subscription_consume"
API_RECORD_PACK_CONSUME = "pack_quota_consume"
API_RECORD_USAGE_PACK_PURCHASE = "usage_pack_purchase"
API_RECORD_SUBSCRIPTION_GRANT = "subscription_grant"

CONSUMED_FROM_SUBSCRIPTION = "subscription"
CONSUMED_FROM_PACK = "pack"

QUOTA_RECORD_ALLOWED_DAYS: frozenset[int] = frozenset({1, 7, 30, 90})
QUOTA_RECORD_DEFAULT_DAYS = 30
QUOTA_RECORD_MAX_EXPORT_ROWS = 10_000
