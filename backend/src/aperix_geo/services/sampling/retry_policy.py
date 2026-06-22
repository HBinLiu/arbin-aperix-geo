"""Retry policy for transient sampling / LLM failures."""

from __future__ import annotations

from aperix_geo.config import get_settings
from aperix_geo.services.providers.errors import (
    is_transient_http_status,
    parse_http_status_from_message,
)
from aperix_geo.services.sampling.llm import SamplingLLMError
from aperix_geo.services.sampling.llm_limits import SamplingRateLimitError
from aperix_geo.services.crawl.limits import CrawlRateLimitError
from aperix_geo.utils.cache import SingleFlightWaitTimeout
from aperix_geo.utils.db_retry import is_retryable_db_error


def is_retryable_sampling_error(exc: BaseException) -> bool:
    """True for timeouts, rate limits, and other likely-transient provider failures."""
    if isinstance(exc, (SamplingRateLimitError, CrawlRateLimitError, SingleFlightWaitTimeout)):
        return True
    if isinstance(exc, (TimeoutError, ConnectionError, OSError)):
        return True
    if is_retryable_db_error(exc):
        return True
    if isinstance(exc, SamplingLLMError):
        return _is_retryable_llm_error(exc)
    return False


def _is_retryable_llm_error(exc: SamplingLLMError) -> bool:
    from aperix_geo.services.alerts.billing import is_billing_provider_error

    if is_billing_provider_error(str(exc), exc.status_code):
        return False
    if exc.retryable is True:
        return True
    if exc.retryable is False:
        return False
    if exc.status_code is not None:
        return is_transient_http_status(exc.status_code)
    return _message_suggests_transient(str(exc))


def _message_suggests_transient(message: str) -> bool:
    """Fallback when provider did not attach structured fields."""
    status = parse_http_status_from_message(message)
    if status is not None:
        return is_transient_http_status(status)
    lower = message.lower()
    return "timeout" in lower or "timed out" in lower


def retry_countdown_seconds(
    retry_count: int,
    *,
    base_s: int | None = None,
    cap_s: int | None = None,
) -> int:
    """Exponential backoff for Celery retries, capped (defaults from settings)."""
    settings = get_settings()
    base = base_s if base_s is not None else settings.sampling_retry_base_s
    cap = cap_s if cap_s is not None else settings.sampling_retry_cap_s
    attempt = max(0, retry_count)
    return min(cap, base * (2**attempt))
