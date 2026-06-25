"""On-demand brand report preview and PDF export."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import HTMLResponse, Response

from aperix_geo.api.deps import CurrentUser, DbSession, get_subject_for_user
from aperix_geo.api.schemas.report_query import BrandReportParams
from aperix_geo.services.report.build import build_brand_report_payload
from aperix_geo.services.report.export import (
    assert_export_allowed,
    export_usage_for_user,
    record_brand_report_export,
)
from aperix_geo.services.report.render import html_to_pdf_bytes, render_brand_report_html
from aperix_geo.utils.datetime import parse_iso_datetime

router = APIRouter(tags=["reports"])


def _parse_window(params: BrandReportParams):
    dt_from = parse_iso_datetime(params.start_date)
    dt_to = parse_iso_datetime(params.end_date)
    if dt_from > dt_to:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="start_date must be before end_date")
    return dt_from, dt_to


@router.get("/subjects/{subject_id}/reports/export-usage")
def brand_report_export_usage(subject_id: UUID, db: DbSession, current: CurrentUser) -> dict:
    get_subject_for_user(db, current, subject_id, with_competitors=True)
    return export_usage_for_user(db, user=current)


@router.post("/subjects/{subject_id}/reports/preview")
def preview_brand_report(
    subject_id: UUID,
    params: BrandReportParams,
    db: DbSession,
    current: CurrentUser,
) -> HTMLResponse:
    subject = get_subject_for_user(db, current, subject_id, with_competitors=True)
    dt_from, dt_to = _parse_window(params)
    payload = build_brand_report_payload(
        db,
        subject=subject,
        dt_from=dt_from,
        dt_to=dt_to,
        entity_id=params.entity_id,
        platform=params.platform,
        topic_id=params.topic_id,
    )
    return HTMLResponse(content=render_brand_report_html(payload))


@router.post("/subjects/{subject_id}/reports/export.pdf")
def export_brand_report_pdf(
    subject_id: UUID,
    params: BrandReportParams,
    db: DbSession,
    current: CurrentUser,
) -> Response:
    subject = get_subject_for_user(db, current, subject_id, with_competitors=True)
    assert_export_allowed(db, user=current)
    dt_from, dt_to = _parse_window(params)
    payload = build_brand_report_payload(
        db,
        subject=subject,
        dt_from=dt_from,
        dt_to=dt_to,
        entity_id=params.entity_id,
        platform=params.platform,
        topic_id=params.topic_id,
    )
    html = render_brand_report_html(payload)
    try:
        pdf_bytes = html_to_pdf_bytes(html)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="PDF 引擎未就绪，请安装 Playwright Chromium",
        ) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"PDF 生成失败: {exc}",
        ) from exc

    record_brand_report_export(
        db,
        user=current,
        subject_id=subject.id,
        window_start=dt_from,
        window_end=dt_to,
        entity_id=params.entity_id,
        platform=params.platform,
        topic_ids=params.topic_id,
    )

    brand = payload.get("meta", {}).get("brand") or subject.brand or "brand"
    safe_name = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in brand)[:48]
    filename = f"brand-report-{safe_name}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
