"""Tests for monitoring_scope helpers."""

from aperix_geo.utils.coerce import (
    normalize_monitoring_scope,
)


def test_normalize_monitoring_scope() -> None:
    assert normalize_monitoring_scope({"region": " CN ", "language": " zh-CN ", "note": " "}) == {
        "region": "CN",
        "language": "zh-CN",
    }


def test_normalize_monitoring_scope_preserves_niche_profile() -> None:
    assert normalize_monitoring_scope(
        {
            "region": "CN",
            "niche_profile": {
                "industry": " 跨境支付 ",
                "core_features": "API",
                "target_customers": "出海企业",
                "ignored": "x",
            },
        }
    ) == {
        "region": "CN",
        "niche_profile": {
            "industry": "跨境支付",
            "core_features": "API",
            "target_customers": "出海企业",
        },
    }

