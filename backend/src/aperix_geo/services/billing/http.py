"""Map billing exceptions to HTTP responses."""

from fastapi import HTTPException, status

from aperix_geo.services.billing.exceptions import QuotaExceededError


def quota_exceeded_http_exception(exc: QuotaExceededError) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_402_PAYMENT_REQUIRED,
        detail={"dimension": exc.dimension, "message": str(exc)},
    )
