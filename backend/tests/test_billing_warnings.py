"""Tests for AI quota warning thresholds."""

from __future__ import annotations

from aperix_geo.services.billing.warnings import compute_quota_warning


def test_compute_quota_warning_none_when_plenty_remaining() -> None:
    assert compute_quota_warning(
        monthly_limit=2500,
        monthly_remaining=2000,
        usage_pack_balance=0,
        ai_requests_available=2000,
    ) is None


def test_compute_quota_warning_20_percent() -> None:
    warning = compute_quota_warning(
        monthly_limit=1000,
        monthly_remaining=150,
        usage_pack_balance=0,
        ai_requests_available=150,
    )
    assert warning is not None
    assert warning.code == "20pct"


def test_compute_quota_warning_exhausted() -> None:
    warning = compute_quota_warning(
        monthly_limit=1000,
        monthly_remaining=0,
        usage_pack_balance=0,
        ai_requests_available=0,
    )
    assert warning is not None
    assert warning.code == "0pct"
