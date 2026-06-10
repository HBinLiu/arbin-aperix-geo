"""Tests for sampling LLM rate limit helper."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from aperix_geo.services.sampling.rate_limit import SamplingRateLimitError, check_llm_rate_limit


@patch("aperix_geo.services.sampling.rate_limit.rate_limit_for_platform", return_value=("deepseek", 2))
@patch("aperix_geo.services.sampling.rate_limit.shared_redis_client")
def test_check_llm_rate_limit_uses_shared_client(mock_client: MagicMock, _mock_limit: MagicMock) -> None:
    redis = MagicMock()
    redis.incr.return_value = 1
    mock_client.return_value = redis

    check_llm_rate_limit("deepseek")

    redis.incr.assert_called_once()
    redis.expire.assert_called_once()


@patch("aperix_geo.services.sampling.rate_limit.rate_limit_for_platform", return_value=("deepseek", 2))
@patch("aperix_geo.services.sampling.rate_limit.shared_redis_client")
def test_check_llm_rate_limit_raises_when_exceeded(mock_client: MagicMock, _mock_limit: MagicMock) -> None:
    redis = MagicMock()
    redis.incr.return_value = 3
    mock_client.return_value = redis

    with pytest.raises(SamplingRateLimitError):
        check_llm_rate_limit("deepseek")


@patch("aperix_geo.services.sampling.rate_limit.rate_limit_for_platform", return_value=("deepseek", 2))
@patch("aperix_geo.services.sampling.rate_limit.shared_redis_client", return_value=None)
def test_check_llm_rate_limit_skips_when_redis_unavailable(_mock_client: MagicMock, _mock_limit: MagicMock) -> None:
    check_llm_rate_limit("deepseek")
