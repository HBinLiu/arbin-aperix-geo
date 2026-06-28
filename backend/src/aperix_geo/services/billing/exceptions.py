"""Billing quota exceptions."""


class SubscriptionInactiveError(Exception):
    """Tenant subscription is missing or not usable."""


class QuotaExceededError(Exception):
    """Tenant has exhausted AI request quota."""

    def __init__(self, *, dimension: str = "ai_requests", message: str | None = None) -> None:
        self.dimension = dimension
        super().__init__(message or f"Quota exceeded: {dimension}")
