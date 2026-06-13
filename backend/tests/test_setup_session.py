"""Tests for setup discovery session cache."""

from __future__ import annotations

from unittest.mock import patch

from aperix_geo.services.setup.cache import (
    create_session,
    delete_session,
    get_session,
    update_session,
)


@patch("aperix_geo.services.setup.cache.session.require_redis_client")
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


@patch("aperix_geo.services.setup.cache.session.require_redis_client")
def test_update_session_merges(mock_redis_fn, mock_redis) -> None:
    mock_redis_fn.return_value = mock_redis

    session_id = create_session(user_id="u2", payload={"micro_keywords": ["a", "b"]})
    ok = update_session(user_id="u2", session_id=session_id, patch={"micro_keywords": ["c", "d"]})
    assert ok is True
    loaded = get_session(user_id="u2", session_id=session_id)
    assert loaded["micro_keywords"] == ["c", "d"]


@patch("aperix_geo.services.setup.cache.session.require_redis_client")
def test_update_session_removes_none_keys(mock_redis_fn, mock_redis) -> None:
    mock_redis_fn.return_value = mock_redis

    session_id = create_session(
        user_id="u4",
        payload={"research_payload": {"site_data": {"title": "x"}}, "profile": {}},
    )
    ok = update_session(user_id="u4", session_id=session_id, patch={"research_payload": None})
    assert ok is True
    loaded = get_session(user_id="u4", session_id=session_id)
    assert loaded is not None
    assert "research_payload" not in loaded


@patch("aperix_geo.services.setup.cache.session.require_redis_client")
def test_create_session_uses_ttl(mock_redis_fn, mock_redis) -> None:
    mock_redis_fn.return_value = mock_redis

    with patch("aperix_geo.services.setup.cache.session.get_settings") as mock_settings:
        mock_settings.return_value.setup_session_ttl_s = 3600
        session_id = create_session(user_id="u5", payload={"target": "example.com"})

    assert len(session_id) == 32
    mock_redis.setex.assert_called_once()
    args = mock_redis.setex.call_args[0]
    assert args[1] == 3600
    mock_redis.set.assert_not_called()


@patch("aperix_geo.services.setup.cache.session.require_redis_client")
def test_delete_session(mock_redis_fn, mock_redis) -> None:
    mock_redis_fn.return_value = mock_redis

    session_id = create_session(user_id="u3", payload={"profile_summary": "x"})
    assert get_session(user_id="u3", session_id=session_id) is not None

    assert delete_session(user_id="u3", session_id=session_id) is True
    assert get_session(user_id="u3", session_id=session_id) is None
