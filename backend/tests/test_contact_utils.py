"""Tests for contact normalization."""

import pytest

from aperix_geo.utils.contact import normalize_email, normalize_phone_cn


def test_normalize_email() -> None:
    assert normalize_email("  User@Example.COM ") == "user@example.com"


def test_normalize_email_invalid() -> None:
    with pytest.raises(ValueError):
        normalize_email("not-an-email")


def test_normalize_phone_cn() -> None:
    assert normalize_phone_cn("+86 13800138000") == "13800138000"


def test_normalize_phone_cn_invalid() -> None:
    with pytest.raises(ValueError):
        normalize_phone_cn("12345")
