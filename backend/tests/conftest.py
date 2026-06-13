"""Shared pytest fixtures."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest


@pytest.fixture
def redis_store() -> dict[str, str]:
    return {}


@pytest.fixture
def mock_redis(redis_store: dict[str, str]) -> MagicMock:
    mock_r = MagicMock()
    mock_r.set = MagicMock(side_effect=lambda key, value: redis_store.update({key: value}) or True)
    mock_r.setex = MagicMock(side_effect=lambda key, ttl, value: redis_store.update({key: value}) or True)
    mock_r.get = lambda key: redis_store.get(key)
    mock_r.delete = MagicMock(side_effect=lambda key: int(redis_store.pop(key, None) is not None))
    return mock_r
