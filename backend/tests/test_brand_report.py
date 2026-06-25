"""Tests for on-demand brand report build, render, and export audit."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch
from uuid import uuid4

from aperix_geo.db.models import BrandReportExport, User
from aperix_geo.services.report.export import export_usage_for_user, record_brand_report_export
from aperix_geo.services.report.render import render_brand_report_html


def test_fmt_date_uses_calendar_day_in_offset() -> None:
    from aperix_geo.services.report.render import _fmt_date

    assert _fmt_date("2026-06-25T00:00:00+08:00") == "2026/06/25"
    assert _fmt_date("2026-06-25") == "2026/06/25"


def test_render_brand_report_html_includes_brand_name() -> None:
    payload = {
        "meta": {
            "brand": "Aperix",
            "domain": "aperix.com",
            "own_entity_label": "aperix",
            "period_start": "2026-01-01T00:00:00+00:00",
            "period_end": "2026-01-02T00:00:00+00:00",
            "response_count": 3,
        },
        "overview": {
            "visibility": {"current": 0.42, "rank": 2},
            "mention": {"current": 0.55, "rank": 1},
            "citation": {"current": 0.12, "rank": 3},
            "share_voice": {"current": 0.25, "rank": 2},
            "sentiment": {"current": 72.0, "label": "positive", "rank": 1},
            "average_rank": {"current": 2.1, "rank": 1, "previous": 2.5},
            "visibility_chart": {
                "cur_series": [
                    {"date": "2026-01-01", "values": {"aperix": 0.3}},
                    {"date": "2026-01-02", "values": {"aperix": 0.42}},
                ],
                "pre_series": [],
            },
            "visibility_table": [{"label": "Aperix", "cur_value": 0.42}],
            "topic_table": [
                {
                    "topic_name": "品类",
                    "visibility": {"current": 0.5},
                    "citation": {"current": 0.1},
                    "sentiment": {"label": "positive"},
                    "average_rank": {"current": 2.1},
                }
            ],
        },
        "diagnosis": {
            "summary": {
                "overall_score": 72.5,
                "overall_status": "good",
                "mention": {"health_score": 80.0, "priority_counts": {"high": 1, "medium": 2, "low": 3}},
                "brand_gap": {"health_score": 65.0, "priority_counts": {"high": 0, "medium": 1, "low": 2}},
                "source_gap": {"health_score": 70.0, "priority_counts": {"high": 1, "medium": 1, "low": 1}},
            }
        },
        "context": {
            "key_insight": "Aperix 在选定周期内 AI 可见度 42.0%（第 2 名）。",
            "topic_count": 3,
            "prompt_count": 12,
            "competitors": [{"label": "竞品A", "domain": "a.com"}],
            "platforms": [{"key": "openai", "label": "ChatGPT"}],
            "platform_metrics": [],
            "citation_table": [],
            "share_voice_table": [],
            "diagnosis_items": [],
            "competitor_avg": {"visibility": 0.3, "mention": 0.4, "citation": 0.1, "share_voice": 0.2, "average_rank": 3.2},
        },
    }
    html = render_brand_report_html(payload)
    assert "Aperix" in html
    assert "42.0%" in html
    assert "内容诊断" in html
    assert "核心结论" in html


@patch("aperix_geo.services.report.build.build_dashboard_overview")
@patch("aperix_geo.services.report.build.query_diagnosis_content_summary")
@patch("aperix_geo.services.report.build.count_responses_in_window", return_value=5)
def test_build_brand_report_payload_uses_window(
    _mock_count: MagicMock,
    mock_diag: MagicMock,
    mock_overview: MagicMock,
) -> None:
    from aperix_geo.db.models import Subject, SubjectType
    from aperix_geo.services.report.build import build_brand_report_payload

    subject = Subject(id=uuid4(), tenant_id=uuid4(), type=SubjectType.brand, brand="Aperix")
    dt_from = datetime(2026, 1, 1, tzinfo=UTC)
    dt_to = datetime(2026, 1, 31, tzinfo=UTC)
    mock_overview.return_value = {"visibility": {"current": 0.5}}
    mock_diag.return_value = {"overall_score": 70.0}

    db = MagicMock()
    payload = build_brand_report_payload(db, subject=subject, dt_from=dt_from, dt_to=dt_to)

    assert payload["meta"]["response_count"] == 5
    assert payload["meta"]["period_start"].startswith("2026-01-01")
    mock_overview.assert_called_once()
    mock_diag.assert_called_once()


def test_record_brand_report_export_persists_row() -> None:
    db = MagicMock()
    user = User(id=uuid4(), tenant_id=uuid4())
    subject_id = uuid4()
    dt_from = datetime(2026, 1, 1, tzinfo=UTC)
    dt_to = datetime(2026, 1, 31, tzinfo=UTC)

    captured: dict[str, BrandReportExport] = {}

    def add(obj):
        if isinstance(obj, BrandReportExport):
            captured["row"] = obj

    db.add.side_effect = add

    record_brand_report_export(
        db,
        user=user,
        subject_id=subject_id,
        window_start=dt_from,
        window_end=dt_to,
        entity_id=None,
        platform=None,
        topic_ids=None,
    )

    row = captured["row"]
    assert row.user_id == user.id
    assert row.subject_id == subject_id
    assert row.format == "pdf"
    db.commit.assert_called_once()


def test_export_usage_unlimited_by_default() -> None:
    db = MagicMock()
    db.scalar.return_value = 3
    user = User(id=uuid4(), tenant_id=uuid4())
    usage = export_usage_for_user(db, user=user)
    assert usage["export_count"] == 3
    assert usage["export_limit"] is None
    assert usage["remaining"] is None


@patch("playwright.sync_api.sync_playwright")
def test_html_to_pdf_bytes(mock_sync_playwright: MagicMock) -> None:
    from aperix_geo.services.report.render import html_to_pdf_bytes

    browser = MagicMock()
    page = MagicMock()
    page.pdf.return_value = b"%PDF-1.4"
    browser.new_page.return_value = page
    playwright = MagicMock()
    playwright.chromium.launch.return_value = browser
    mock_sync_playwright.return_value.__enter__.return_value = playwright

    out = html_to_pdf_bytes("<html><body>ok</body></html>")
    assert out.startswith(b"%PDF")
    browser.new_page.assert_called_once_with(viewport={"width": 794, "height": 1123})
    page.emulate_media.assert_called_once_with(media="print")
    page.pdf.assert_called_once()
    assert page.pdf.call_args.kwargs["print_background"] is True
    assert page.pdf.call_args.kwargs["margin"] == {
        "top": "0",
        "right": "0",
        "bottom": "0",
        "left": "0",
    }
