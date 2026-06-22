"""Tests for single-flight coalescing."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from aperix_geo.utils.cache.coalesce import SingleFlightWaitTimeout, run_single_flight


@patch("aperix_geo.utils.cache.coalesce.redis_delete")
@patch("aperix_geo.utils.cache.coalesce.redis_set_nx", return_value=True)
def test_run_single_flight_holder_fetches_once(mock_set_nx: MagicMock, mock_delete: MagicMock) -> None:
    fetch_calls: list[int] = []

    def _fetch() -> str:
        fetch_calls.append(1)
        return "ok"

    out = run_single_flight(
        "digest-a",
        wait_s=1.0,
        read_cache=lambda: None,
        fetch=_fetch,
        lock_prefix="test:lock:",
    )

    assert out == "ok"
    assert fetch_calls == [1]
    mock_set_nx.assert_called_once()
    mock_delete.assert_called_once()


@patch("aperix_geo.utils.cache.coalesce.redis_set_nx", return_value=False)
@patch("aperix_geo.utils.cache.coalesce._wait_for_cache", return_value=None)
def test_run_single_flight_waiter_does_not_fetch_on_timeout(
    _mock_wait: MagicMock,
    _mock_set_nx: MagicMock,
) -> None:
    fetch_calls: list[int] = []

    with pytest.raises(SingleFlightWaitTimeout):
        run_single_flight(
            "digest-b",
            wait_s=1.0,
            read_cache=lambda: None,
            fetch=lambda: fetch_calls.append(1) or "ok",
            lock_prefix="test:lock:",
        )

    assert fetch_calls == []


@patch("aperix_geo.utils.cache.coalesce.redis_set_nx", return_value=False)
@patch("aperix_geo.utils.cache.coalesce._wait_for_cache", return_value="cached")
def test_run_single_flight_waiter_returns_peer_cache(
    _mock_wait: MagicMock,
    _mock_set_nx: MagicMock,
) -> None:
    fetch_calls: list[int] = []

    out = run_single_flight(
        "digest-c",
        wait_s=1.0,
        read_cache=lambda: None,
        fetch=lambda: fetch_calls.append(1) or "ok",
        lock_prefix="test:lock:",
    )

    assert out == "cached"
    assert fetch_calls == []
