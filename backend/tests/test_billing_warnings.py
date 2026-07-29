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


def test_build_quota_warn_template_data_from_yaml() -> None:
    from aperix_geo.services.wechat.template import (
        build_template_data,
        quota_warn_context,
        resolve_quota_warn_template,
    )
    from aperix_geo.services.wechat.templates_config import clear_template_catalog_cache

    clear_template_catalog_cache()
    resolved = resolve_quota_warn_template()
    assert resolved is not None
    template, _jump = resolved
    assert template.key == "quota_warn"
    assert template.template_id.startswith("1gFx")
    data = build_template_data(
        template,
        context=quota_warn_context(
            title="AI 请求额度剩余不足 20%",
            body="当前可用 AI 请求：150 次",
            available=150,
            phone="13800138000",
            reason="额度不足20%",
        ),
    )
    assert data["phone_number9"]["value"] == "13800138000"
    assert data["amount2"]["value"] == "150"
    assert data["const4"]["value"] == "额度不足20%"
