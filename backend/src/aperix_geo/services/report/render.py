"""Render brand report HTML and PDF."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from aperix_geo.utils.datetime import parse_iso_datetime

REPORT_TEMPLATE_VERSION = "2"
_TEMPLATE_DIR = Path(__file__).resolve().parent.parent.parent / "templates"

_SENTIMENT_ZH = {
    "positive": "正面",
    "neutral": "中性",
    "negative": "负面",
}
_STATUS_ZH = {
    "excellent": "优秀",
    "good": "良好",
    "improvement": "待改善",
    "critical": "需关注",
}
_PRIORITY_ZH = {
    "high": "高",
    "medium": "中",
    "low": "低",
}


@lru_cache(maxsize=1)
def _jinja_env() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(_TEMPLATE_DIR)),
        autoescape=select_autoescape(["html", "xml"]),
    )


def _pct(value: float | None) -> str:
    if value is None:
        return "—"
    return f"{value * 100:.1f}%"


def _score(value: float | None) -> str:
    if value is None:
        return "—"
    return f"{value:.1f}"


def _as_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _delta_pct(current: Any, previous: Any) -> str | None:
    cur = _as_float(current)
    prev = _as_float(previous)
    if cur is None or prev is None:
        return None
    diff = (cur - prev) * 100
    sign = "+" if diff > 0 else ""
    return f"{sign}{diff:.1f}%"


def _bar_width(value: float | None, *, scale: float = 1.0) -> float:
    if value is None:
        return 0.0
    return max(0.0, min(100.0, float(value) * 100 * scale))


def _sentiment_zh(label: str | None) -> str:
    if not label:
        return "—"
    return _SENTIMENT_ZH.get(label, label)


def _status_zh(status: str | None) -> str:
    if not status:
        return "—"
    return _STATUS_ZH.get(status, status)


def _priority_zh(priority: str | None) -> str:
    if not priority:
        return "—"
    return _PRIORITY_ZH.get(priority, priority)


def _fmt_date(value: str | None) -> str:
    if not value:
        return "—"
    stripped = value.strip()
    if len(stripped) == 10 and stripped[4] == "-" and stripped[7] == "-":
        y, m, d = stripped.split("-")
        return f"{y}/{m}/{d}"
    dt = parse_iso_datetime(stripped)
    return f"{dt.year:04d}/{dt.month:02d}/{dt.day:02d}"


def _metric_status(current: float | None, benchmark: float | None) -> dict[str, str]:
    if current is None or benchmark is None:
        return {"class": "status-gray", "text": "暂无对比"}
    if current >= benchmark:
        return {"class": "status-green", "text": "领先竞品"}
    if current >= benchmark * 0.85:
        return {"class": "status-orange", "text": "接近均值"}
    return {"class": "status-red", "text": "低于均值"}


def _metric_status_rank(current: float | None, benchmark: float | None) -> dict[str, str]:
    """Lower average rank is better."""
    if current is None or benchmark is None:
        return {"class": "status-gray", "text": "暂无对比"}
    if current <= benchmark:
        return {"class": "status-green", "text": "领先竞品"}
    if current <= benchmark * 1.15:
        return {"class": "status-orange", "text": "接近均值"}
    return {"class": "status-red", "text": "低于均值"}


def _delta_score(current: Any, previous: Any) -> str | None:
    cur = _as_float(current)
    prev = _as_float(previous)
    if cur is None or prev is None:
        return None
    diff = cur - prev
    sign = "+" if diff > 0 else ""
    return f"{sign}{diff:.2f}"


def _svg_area_chart(
    series: list[dict[str, Any]],
    *,
    label: str,
    width: int = 640,
    height: int = 160,
    stroke: str = "#ec783b",
    fill: str = "#ec783b",
) -> str:
    values: list[tuple[str, float]] = []
    for point in series:
        raw = (point.get("values") or {}).get(label)
        if raw is None:
            continue
        values.append((str(point.get("date") or ""), float(raw)))

    if len(values) < 2:
        return ""

    nums = [value for _, value in values]
    max_v = max(nums)
    min_v = min(nums)
    span = max(max_v - min_v, 0.01)
    pad_x, pad_y = 12, 12
    inner_w = width - pad_x * 2
    inner_h = height - pad_y * 2

    coords: list[tuple[float, float]] = []
    for index, (_, value) in enumerate(values):
        x = pad_x + inner_w * index / (len(values) - 1)
        y = pad_y + inner_h * (1 - (value - min_v) / span)
        coords.append((x, y))

    line_points = " ".join(f"{x:.1f},{y:.1f}" for x, y in coords)
    area_path = (
        f"M {coords[0][0]:.1f},{height - pad_y:.1f} "
        + " ".join(f"L {x:.1f},{y:.1f}" for x, y in coords)
        + f" L {coords[-1][0]:.1f},{height - pad_y:.1f} Z"
    )
    first_date = values[0][0]
    last_date = values[-1][0]

    return (
        f'<svg class="trend-chart" viewBox="0 0 {width} {height}" '
        f'role="img" aria-label="可见度趋势">'
        f'<path d="{area_path}" fill="{fill}" fill-opacity="0.16" />'
        f'<polyline fill="none" stroke="{stroke}" stroke-width="2.5" '
        f'stroke-linecap="round" stroke-linejoin="round" points="{line_points}" />'
        f'<text x="{pad_x}" y="{height - 2}" class="chart-axis">{first_date}</text>'
        f'<text x="{width - pad_x}" y="{height - 2}" class="chart-axis" text-anchor="end">{last_date}</text>'
        f"</svg>"
    )


def render_brand_report_html(payload: dict[str, Any]) -> str:
    template = _jinja_env().get_template("report.html")
    return template.render(
        payload=payload,
        pct=_pct,
        score=_score,
        delta_pct=_delta_pct,
        bar_width=_bar_width,
        sentiment_zh=_sentiment_zh,
        status_zh=_status_zh,
        priority_zh=_priority_zh,
        fmt_date=_fmt_date,
        metric_status=_metric_status,
        metric_status_rank=_metric_status_rank,
        delta_score=_delta_score,
        svg_area_chart=_svg_area_chart,
    )


def html_to_pdf_bytes(html: str) -> bytes:
    """Render HTML to PDF via headless Chromium (playwright)."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError("playwright is not installed") from exc

    # A4 @ 96dpi — match layout width to printable page so grids don't clip.
    a4_width_px = 794
    a4_height_px = 1123

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            page = browser.new_page(viewport={"width": a4_width_px, "height": a4_height_px})
            page.emulate_media(media="print")
            page.set_content(html, wait_until="load")
            page.wait_for_timeout(200)
            return page.pdf(
                format="A4",
                print_background=True,
                prefer_css_page_size=True,
                margin={"top": "0", "right": "0", "bottom": "0", "left": "0"},
            )
        finally:
            browser.close()
