"""Tests for setup discovery session cache."""

from __future__ import annotations

from unittest.mock import patch

from aperix_geo.services.setup.session import (
    create_session,
    get_session,
    update_session,
)


@patch("aperix_geo.services.setup.session._redis")
def test_create_and_get_session(mock_redis_fn, mock_redis) -> None:
    mock_redis_fn.return_value = mock_redis

    session_id = create_session(
        user_id="user-1",
        payload={"subject_type": "domain", "target": "example.com", "profile": {}},
    )
    assert len(session_id) == 32

    loaded = get_session(user_id="user-1", session_id=session_id)
    assert loaded is not None
    assert loaded["target"] == "example.com"
    assert loaded["user_id"] == "user-1"


@patch("aperix_geo.services.setup.session._redis")
def test_update_session_merges(mock_redis_fn, mock_redis) -> None:
    mock_redis_fn.return_value = mock_redis

    session_id = create_session(user_id="u2", payload={"micro_keywords": ["a", "b"]})
    ok = update_session(user_id="u2", session_id=session_id, patch={"micro_keywords": ["c", "d"]})
    assert ok is True
    loaded = get_session(user_id="u2", session_id=session_id)
    assert loaded["micro_keywords"] == ["c", "d"]
