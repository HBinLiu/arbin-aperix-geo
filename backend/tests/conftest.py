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
    mock_r.setex = lambda key, ttl, value: redis_store.update({key: value})
    mock_r.get = lambda key: redis_store.get(key)
    return mock_r
