"""Subscription billing and quota enforcement."""

from aperix_geo.services.billing.exceptions import QuotaExceededError, SubscriptionInactiveError
from aperix_geo.services.billing.limits import PlanLimits, effective_limits
from aperix_geo.services.billing.quota import (
    ai_usage_available,
    assert_ai_usage_available,
    assert_can_add_prompts,
    assert_can_create_subject,
    assert_competitor_capacity,
    assert_platform_capacity,
    consume_ai_usage,
    get_limits_for_tenant,
    get_subscription_snapshot,
    remaining_prompt_slots,
)

__all__ = [
    "PlanLimits",
    "QuotaExceededError",
    "SubscriptionInactiveError",
    "ai_usage_available",
    "assert_ai_usage_available",
    "assert_can_add_prompts",
    "assert_can_create_subject",
    "assert_competitor_capacity",
    "assert_platform_capacity",
    "consume_ai_usage",
    "effective_limits",
    "get_limits_for_tenant",
    "get_subscription_snapshot",
    "remaining_prompt_slots",
]
