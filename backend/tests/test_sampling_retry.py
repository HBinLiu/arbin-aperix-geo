"""Tests for sampling retry policy."""

from __future__ import annotations

from aperix_geo.services.providers.errors import DoubaoProviderError
from aperix_geo.services.sampling.llm import SamplingLLMError, sampling_llm_error_from
from aperix_geo.services.sampling.rate_limit import SamplingRateLimitError
from aperix_geo.services.sampling.retry_policy import is_retryable_sampling_error, retry_countdown_seconds


def test_is_retryable_timeout_and_http_status() -> None:
    assert is_retryable_sampling_error(SamplingLLMError("DeepSeek timeout: read timed out"))
    assert is_retryable_sampling_error(SamplingLLMError("Doubao HTTP 502: bad gateway"))
    assert is_retryable_sampling_error(SamplingLLMError("Qianwen HTTP 429: too many requests"))
    assert is_retryable_sampling_error(SamplingRateLimitError("LLM rate limit exceeded"))


def test_is_retryable_structured_fields() -> None:
    assert is_retryable_sampling_error(SamplingLLMError("upstream", status_code=502))
    assert is_retryable_sampling_error(SamplingLLMError("timeout", retryable=True))
    assert not is_retryable_sampling_error(SamplingLLMError("auth", status_code=401))
    assert not is_retryable_sampling_error(SamplingLLMError("config", retryable=False))


def test_sampling_llm_error_from_provider() -> None:
    wrapped = sampling_llm_error_from(
        DoubaoProviderError("Doubao HTTP 502: bad gateway", status_code=502)
    )
    assert wrapped.status_code == 502
    assert is_retryable_sampling_error(wrapped)


def test_is_not_retryable_configuration_errors() -> None:
    assert not is_retryable_sampling_error(SamplingLLMError("Unknown or unconfigured platform: foo"))
    assert not is_retryable_sampling_error(SamplingLLMError("Doubao API key is not configured"))
    assert not is_retryable_sampling_error(SamplingLLMError("Doubao HTTP 401: unauthorized"))


def test_retry_countdown_exponential() -> None:
    assert retry_countdown_seconds(0) == 20
    assert retry_countdown_seconds(1) == 40
    assert retry_countdown_seconds(2) == 80
    assert retry_countdown_seconds(3) == 120
    assert retry_countdown_seconds(10) == 120
