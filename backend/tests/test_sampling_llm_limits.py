"""Tests for sampling LLM limits helper."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from aperix_geo.services.sampling.llm_limits import (
    SamplingRateLimitError,
    llm_sampling_slot,
    provider_limits_for_platform,
)


@patch(
    "aperix_geo.services.sampling.llm_limits.provider_limits_for_platform",
    return_value=("deepseek", 2, 5),
)
@patch("aperix_geo.services.sampling.llm_limits.shared_redis_client")
def test_llm_sampling_slot_raises_when_minute_exceeded(mock_client: MagicMock, _mock_limits: MagicMock) -> None:
    redis = MagicMock()
    redis.incr.return_value = 3
    mock_client.return_value = redis

    with pytest.raises(SamplingRateLimitError, match="rate limit exceeded"):
        with llm_sampling_slot("deepseek"):
            pass


@patch(
    "aperix_geo.services.sampling.llm_limits.provider_limits_for_platform",
    return_value=("deepseek", 2, 5),
)
@patch("aperix_geo.services.sampling.llm_limits.shared_redis_client")
def test_llm_sampling_slot_uses_minute_key(mock_client: MagicMock, _mock_limits: MagicMock) -> None:
    redis = MagicMock()
    redis.incr.side_effect = [1, 1]
    redis.ttl.return_value = 600
    redis.decr.return_value = 0
    mock_client.return_value = redis

    with llm_sampling_slot("deepseek"):
        pass

    assert "llm_rl" in redis.incr.call_args_list[0].args[0]
    redis.expire.assert_called()


@patch(
    "aperix_geo.services.sampling.llm_limits.provider_limits_for_platform",
    return_value=("deepseek", 30, 2),
)
@patch("aperix_geo.services.sampling.llm_limits.shared_redis_client")
def test_llm_sampling_slot_acquires_and_releases_inflight(mock_client: MagicMock, _mock_limits: MagicMock) -> None:
    redis = MagicMock()
    redis.incr.side_effect = [1, 1]
    redis.ttl.return_value = 600
    redis.decr.return_value = 0
    mock_client.return_value = redis

    with llm_sampling_slot("deepseek") as provider:
        assert provider == "deepseek"

    assert redis.incr.call_count == 2
    assert "llm_inflight" in redis.incr.call_args_list[1].args[0]
    redis.decr.assert_called_once()
    redis.delete.assert_called_once()


@patch(
    "aperix_geo.services.sampling.llm_limits.provider_limits_for_platform",
    return_value=("deepseek", 30, 2),
)
@patch("aperix_geo.services.sampling.llm_limits.shared_redis_client")
def test_llm_sampling_slot_raises_when_inflight_exceeded(mock_client: MagicMock, _mock_limits: MagicMock) -> None:
    redis = MagicMock()
    redis.incr.side_effect = [1, 3]
    redis.ttl.return_value = 600
    mock_client.return_value = redis

    with pytest.raises(SamplingRateLimitError, match="in-flight limit exceeded"):
        with llm_sampling_slot("deepseek"):
            pass

    redis.decr.assert_called_once()


@patch(
    "aperix_geo.services.sampling.llm_limits.provider_limits_for_platform",
    return_value=("deepseek", 2, 5),
)
@patch("aperix_geo.services.sampling.llm_limits.shared_redis_client", return_value=None)
def test_llm_sampling_slot_raises_when_redis_unavailable(_mock_client: MagicMock, _mock_limits: MagicMock) -> None:
    with pytest.raises(SamplingRateLimitError, match="Redis unavailable"):
        with llm_sampling_slot("deepseek"):
            pass


@patch("aperix_geo.services.sampling.llm_limits.rate_limit_for_platform", return_value=("doubao", 30))
@patch("aperix_geo.services.sampling.llm_limits.get_settings")
def test_provider_limits_for_platform(mock_settings: MagicMock, _mock_rate: MagicMock) -> None:
    mock_settings.return_value.sampling_llm_max_inflight = 12
    assert provider_limits_for_platform("doubao") == ("doubao", 30, 12)
