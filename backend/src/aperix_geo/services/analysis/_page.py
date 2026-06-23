"""Period/rank/pagination helpers for analysis pages."""

from __future__ import annotations

from typing import Any

from aperix_geo.services.analysis.entity import AnalysisEntity


def metric_period(
    current: float | None,
    previous: float | None,
    *,
    has_previous: bool,
) -> dict[str, float | None]:
    return {
        "current": current,
        "previous": previous if has_previous else None,
    }


def previous_value(value: float | None, *, has_previous: bool) -> float | None:
    return value if has_previous else None


def label_rank(share: dict[str, float | None], label: str) -> int | None:
    if not share or label not in share:
        return None
    ranked = sorted(
        share.keys(),
        key=lambda key: share.get(key) if share.get(key) is not None else -1,
        reverse=True,
    )
    try:
        return ranked.index(label) + 1
    except ValueError:
        return None


def metric_with_rank(
    current: float | None,
    previous: float | None,
    share: dict[str, float | None],
    rank_label: str,
) -> dict[str, float | int | None]:
    return {
        "current": current,
        "previous": previous,
        "rank": label_rank(share, rank_label),
    }


def build_rank_table_rows(
    current: dict[str, float | None],
    previous: dict[str, float | None] | None,
    *,
    entities: list[AnalysisEntity],
    has_previous: bool,
) -> list[dict[str, Any]]:
    prev = previous or {}
    display = {entity.label: entity.display_name for entity in entities}
    domains = {entity.label: entity.domain for entity in entities}
    rows: list[dict[str, Any]] = []
    for label in sorted(
        current.keys(),
        key=lambda key: current.get(key) if current.get(key) is not None else -1,
        reverse=True,
    ):
        pre_value: float | None = None
        if has_previous:
            raw = prev.get(label)
            pre_value = float(raw) if raw is not None else None
        rows.append(
            {
                "id": label,
                "label": display.get(label, label),
                "domain": domains.get(label, ""),
                "cur_value": current.get(label),
                "pre_value": pre_value,
            }
        )
    return rows


def normalize_pagination(
    page: int,
    page_size: int,
    *,
    max_page_size: int = 100,
) -> tuple[int, int]:
    safe_page = max(1, page)
    safe_page_size = max(1, min(page_size, max_page_size))
    return safe_page, safe_page_size
