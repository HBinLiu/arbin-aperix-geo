"""Tests for sampling debug guard."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from aperix_geo.services.sampling.debug import assert_sampling_debug_access


def _settings(*, enabled: bool, secret: str = "secret") -> MagicMock:
    s = MagicMock()
    s.sampling_debug_enabled = enabled
    s.sampling_debug_secret = secret
    return s


@patch("aperix_geo.services.sampling.debug.get_settings")
def test_debug_disabled_returns_404(mock_get_settings: MagicMock) -> None:
    mock_get_settings.return_value = _settings(enabled=False)
    with pytest.raises(HTTPException) as exc:
        assert_sampling_debug_access("secret")
    assert exc.value.status_code == 404


@patch("aperix_geo.services.sampling.debug.get_settings")
def test_debug_enabled_without_secret_returns_503(mock_get_settings: MagicMock) -> None:
    mock_get_settings.return_value = _settings(enabled=True, secret="")
    with pytest.raises(HTTPException) as exc:
        assert_sampling_debug_access("secret")
    assert exc.value.status_code == 503


@patch("aperix_geo.services.sampling.debug.get_settings")
def test_debug_wrong_secret_returns_403(mock_get_settings: MagicMock) -> None:
    mock_get_settings.return_value = _settings(enabled=True, secret="expected")
    with pytest.raises(HTTPException) as exc:
        assert_sampling_debug_access("wrong")
    assert exc.value.status_code == 403


@patch("aperix_geo.services.sampling.debug.get_settings")
def test_debug_valid_secret_passes(mock_get_settings: MagicMock) -> None:
    mock_get_settings.return_value = _settings(enabled=True, secret="expected")
    assert_sampling_debug_access("expected") is None
