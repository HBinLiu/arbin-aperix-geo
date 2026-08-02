"""Map billing exceptions to HTTP responses."""

from __future__ import annotations

from fastapi import HTTPException, status

from aperix_geo.services.billing.exceptions import QuotaExceededError, SubscriptionInactiveError

_DEFAULT_SUBSCRIPTION_INACTIVE_DETAIL = "订阅已过期，请续订后再试"

CODE_SUBSCRIPTION_INACTIVE = "subscription_inactive"
CODE_QUOTA_EXCEEDED = "quota_exceeded"


def quota_exceeded_http_exception(exc: QuotaExceededError) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_402_PAYMENT_REQUIRED,
        detail={
            "code": CODE_QUOTA_EXCEEDED,
            "dimension": exc.dimension,
            "message": str(exc),
        },
    )


def subscription_inactive_http_exception(
    exc: SubscriptionInactiveError | None = None,
    *,
    detail: str = _DEFAULT_SUBSCRIPTION_INACTIVE_DETAIL,
) -> HTTPException:
    _ = exc
    return HTTPException(
        status_code=status.HTTP_402_PAYMENT_REQUIRED,
        detail={
            "code": CODE_SUBSCRIPTION_INACTIVE,
            "message": detail,
        },
    )


def billing_http_exception(
    exc: Exception,
    *,
    inactive_detail: str = _DEFAULT_SUBSCRIPTION_INACTIVE_DETAIL,
) -> HTTPException:
    """Map QuotaExceeded / SubscriptionInactive to 402; other types propagate."""
    if isinstance(exc, SubscriptionInactiveError):
        return subscription_inactive_http_exception(exc, detail=inactive_detail)
    if isinstance(exc, QuotaExceededError):
        return quota_exceeded_http_exception(exc)
    raise exc
