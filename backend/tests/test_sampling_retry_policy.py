"""Tests for sampling retry policy."""

from aperix_geo.services.crawl.limits import CrawlRateLimitError
from aperix_geo.services.sampling.llm_limits import SamplingRateLimitError
from aperix_geo.services.sampling.retry_policy import is_retryable_sampling_error
from aperix_geo.utils.cache import SingleFlightWaitTimeout


def test_is_retryable_sampling_error_includes_crawl_rate_limit() -> None:
    assert is_retryable_sampling_error(CrawlRateLimitError("limited")) is True


def test_is_retryable_sampling_error_includes_single_flight_timeout() -> None:
    assert is_retryable_sampling_error(SingleFlightWaitTimeout("key")) is True


def test_is_retryable_sampling_error_includes_llm_rate_limit() -> None:
    assert is_retryable_sampling_error(SamplingRateLimitError("limited")) is True
