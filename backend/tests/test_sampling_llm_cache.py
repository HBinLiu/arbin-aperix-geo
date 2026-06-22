"""Tests for LLM result cache used across sampling retries."""

from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import uuid4

from aperix_geo.services.providers.result import SamplingChatResult
from aperix_geo.services.sampling.cache.llm_result import (
    _from_payload,
    _to_payload,
    clear_cached_llm_result,
    load_cached_llm_result,
    save_cached_llm_result,
)


def test_llm_result_payload_round_trip() -> None:
    original = SamplingChatResult(
        text="hello",
        usage={"completion_tokens": 10},
        latency_ms=1234,
        source_urls=("https://example.com",),
        web_search_mode="searxng",
    )
    restored = _from_payload(_to_payload(original))
    assert restored == original


@patch("aperix_geo.services.sampling.cache.llm_result.redis_get_json")
@patch("aperix_geo.services.sampling.cache.llm_result.redis_set_json_exat")
def test_save_then_load_cached_llm_result(mock_set: MagicMock, mock_get: MagicMock) -> None:
    response_id = uuid4()
    result = SamplingChatResult(text="cached", usage={}, latency_ms=1)

    stored: dict = {}

    def _set(key: str, value: dict, *, expires_at: int) -> None:
        stored["key"] = key
        stored["value"] = value

    mock_set.side_effect = _set
    mock_get.side_effect = lambda key: stored.get("value")

    save_cached_llm_result(response_id, result)
    loaded = load_cached_llm_result(response_id)
    assert loaded == result
    assert str(response_id) in stored["key"]


@patch("aperix_geo.services.sampling.cache.llm_result.redis_delete")
def test_clear_cached_llm_result(mock_delete: MagicMock) -> None:
    response_id = uuid4()
    clear_cached_llm_result(response_id)
    mock_delete.assert_called_once()
