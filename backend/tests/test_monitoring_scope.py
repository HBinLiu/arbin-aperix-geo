"""Tests for monitoring_scope helpers."""

from aperix_geo.utils.coerce import (
    normalize_monitoring_scope,
)


def test_normalize_monitoring_scope() -> None:
    assert normalize_monitoring_scope({"region": " CN ", "language": " zh-CN ", "note": " "}) == {
        "region": "CN",
        "language": "zh-CN",
    }

