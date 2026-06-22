"""DB-side pagination and summary aggregation for diagnosis content."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from aperix_geo.db.models import EntityKind, Subject
from aperix_geo.services.analysis.diagnosis import (
    _merged_diagnosis_gap_metrics,
    diagnosis_issue_type,
    gap_action_priority,
    mention_action_priority,
    overall_action_priority,
    overall_diagnosis_status,
)
from aperix_geo.services.analysis.entity import own_entity
from aperix_geo.services.analysis.signal_load import load_llm_response_signals

_SCOPED_CTES = """
scoped AS (
    SELECT
        prompt_id,
        platform,
        response_id,
        entity_kind,
        mentioned,
        mention_count,
        mention_rank,
        has_domain_link
    FROM tb_llm_response_signals
    WHERE subject_id = :subject_id
      AND created_at >= :dt_from
      AND created_at <= :dt_to
      AND entity_kind IN (:own_kind, :competitor_kind)
),
response_flags AS (
    SELECT
        prompt_id,
        platform,
        response_id,
        MAX(CASE WHEN entity_kind = :own_kind AND mentioned THEN 1 ELSE 0 END)::int AS own_mentioned,
        MAX(CASE WHEN entity_kind = :own_kind AND has_domain_link THEN 1 ELSE 0 END)::int AS own_link,
        MAX(CASE WHEN entity_kind = :competitor_kind AND mentioned THEN 1 ELSE 0 END)::int AS comp_mentioned,
        MAX(CASE WHEN entity_kind = :competitor_kind AND has_domain_link THEN 1 ELSE 0 END)::int AS comp_link
    FROM scoped
    GROUP BY prompt_id, platform, response_id
),
platform_gap AS (
    SELECT
        prompt_id,
        platform,
        COUNT(*) FILTER (WHERE comp_mentioned = 1) AS brand_total_count,
        COUNT(*) FILTER (WHERE comp_mentioned = 1 AND own_mentioned = 1) AS brand_own_count,
        CASE
            WHEN COUNT(*) FILTER (WHERE comp_mentioned = 1) > 0 THEN ROUND(
                1.0 - COUNT(*) FILTER (WHERE comp_mentioned = 1 AND own_mentioned = 1)::numeric
                    / COUNT(*) FILTER (WHERE comp_mentioned = 1),
                4
            )
            ELSE 0
        END AS brand_gap_rate,
        COUNT(*) FILTER (WHERE comp_link = 1) AS source_total_count,
        COUNT(*) FILTER (WHERE comp_link = 1 AND own_link = 1) AS source_own_count,
        CASE
            WHEN COUNT(*) FILTER (WHERE comp_link = 1) > 0 THEN ROUND(
                1.0 - COUNT(*) FILTER (WHERE comp_link = 1 AND own_link = 1)::numeric
                    / COUNT(*) FILTER (WHERE comp_link = 1),
                4
            )
            ELSE 0
        END AS source_gap_rate
    FROM response_flags
    GROUP BY prompt_id, platform
),
brand_max AS (
    SELECT DISTINCT ON (prompt_id)
        prompt_id,
        brand_gap_rate,
        brand_own_count,
        brand_total_count
    FROM platform_gap
    ORDER BY prompt_id, brand_gap_rate DESC, platform ASC
),
source_max AS (
    SELECT DISTINCT ON (prompt_id)
        prompt_id,
        source_gap_rate,
        source_own_count,
        source_total_count
    FROM platform_gap
    ORDER BY prompt_id, source_gap_rate DESC, platform ASC
),
gap_platforms AS (
    SELECT
        prompt_id,
        ARRAY_AGG(DISTINCT platform ORDER BY platform) AS platforms
    FROM platform_gap
    WHERE brand_gap_rate > 0 OR source_gap_rate > 0
    GROUP BY prompt_id
),
own_mention AS (
    SELECT
        prompt_id,
        COUNT(DISTINCT response_id) AS mention_total_count,
        COUNT(DISTINCT response_id) FILTER (WHERE mentioned) AS mention_own_count,
        ROUND(
            COUNT(DISTINCT response_id) FILTER (WHERE mentioned)::numeric
                / NULLIF(COUNT(DISTINCT response_id), 0),
            4
        ) AS mention_rate,
        ROUND(
            AVG(mention_rank) FILTER (WHERE mentioned AND mention_rank > 0),
            2
        ) AS average_rank
    FROM scoped
    WHERE entity_kind = :own_kind
    GROUP BY prompt_id
)
"""

_GAP_ITEM_CTES = """
merged AS (
    SELECT
        p.id AS prompt_id,
        p.text AS prompt_text,
        COALESCE(gp.platforms, ARRAY[]::text[]) AS platforms,
        COALESCE(bm.brand_gap_rate, 0)::float AS brand_gap_rate,
        COALESCE(bm.brand_own_count, 0)::int AS brand_own_count,
        COALESCE(bm.brand_total_count, 0)::int AS brand_total_count,
        COALESCE(sm.source_gap_rate, 0)::float AS source_gap_rate,
        COALESCE(sm.source_own_count, 0)::int AS source_own_count,
        COALESCE(sm.source_total_count, 0)::int AS source_total_count,
        COALESCE(om.mention_rate, 0)::float AS mention_rate,
        COALESCE(om.mention_own_count, 0)::int AS mention_own_count,
        COALESCE(om.mention_total_count, 0)::int AS mention_total_count,
        om.average_rank::float AS average_rank
    FROM tb_prompts p
    LEFT JOIN gap_platforms gp ON gp.prompt_id = p.id
    LEFT JOIN brand_max bm ON bm.prompt_id = p.id
    LEFT JOIN source_max sm ON sm.prompt_id = p.id
    LEFT JOIN own_mention om ON om.prompt_id = p.id
    WHERE p.subject_id = :subject_id
      AND (
          COALESCE(bm.brand_gap_rate, 0) > 0
          OR COALESCE(sm.source_gap_rate, 0) > 0
          OR COALESCE(om.mention_rate, 0) < 0.5
          OR (
              COALESCE(om.mention_rate, 0) >= 0.5
              AND om.average_rank IS NOT NULL
              AND om.average_rank > 3
          )
      )
),
with_priorities AS (
    SELECT
        merged.*,
        CASE
            WHEN mention_rate <= 0 THEN 0
            WHEN mention_rate < 0.5 THEN 1
            WHEN average_rank IS NOT NULL AND average_rank > 3 THEN 1
            ELSE 2
        END AS mention_priority_rank,
        CASE
            WHEN brand_gap_rate >= 0.8 THEN 0
            WHEN brand_gap_rate >= 0.5 THEN 1
            ELSE 2
        END AS brand_gap_priority_rank,
        CASE
            WHEN source_gap_rate >= 0.8 THEN 0
            WHEN source_gap_rate >= 0.5 THEN 1
            ELSE 2
        END AS source_gap_priority_rank
    FROM merged
),
with_overall AS (
    SELECT
        with_priorities.*,
        LEAST(
            mention_priority_rank,
            brand_gap_priority_rank,
            source_gap_priority_rank
        ) AS priority_rank
    FROM with_priorities
)
"""

_DIAGNOSIS_CONTENT_PAGE_SQL = f"""
WITH {_SCOPED_CTES},
{_GAP_ITEM_CTES},
numbered AS (
    SELECT
        with_overall.*,
        COUNT(*) OVER () AS total_count
    FROM with_overall
)
SELECT *
FROM numbered
ORDER BY {{order_clause}}
LIMIT :limit OFFSET :offset
"""

_DIAGNOSIS_CONTENT_SUMMARY_SQL = f"""
WITH {_SCOPED_CTES},
{_GAP_ITEM_CTES},
mention_rows AS (
    SELECT
        om.prompt_id,
        COALESCE(om.mention_rate, 0)::float AS mention_rate,
        om.average_rank::float AS average_rank,
        CASE
            WHEN COALESCE(om.mention_rate, 0) <= 0 THEN 0
            WHEN COALESCE(om.mention_rate, 0) < 0.5 THEN 1
            WHEN om.average_rank IS NOT NULL AND om.average_rank > 3 THEN 1
            ELSE 2
        END AS mention_priority_rank
    FROM own_mention om
    INNER JOIN tb_prompts p ON p.id = om.prompt_id AND p.subject_id = :subject_id
)
SELECT
    (SELECT COUNT(*) FROM mention_rows) AS mention_prompt_count,
    (SELECT COUNT(*) FROM with_overall) AS gap_prompt_count,
    COALESCE(
        (SELECT ROUND(AVG(mention_rate)::numeric * 100, 1) FROM mention_rows),
        0
    )::float AS mention_health,
    COALESCE(
        (SELECT COUNT(*) FROM with_overall WHERE mention_priority_rank = 0),
        0
    )::int AS mention_high,
    COALESCE(
        (SELECT COUNT(*) FROM with_overall WHERE mention_priority_rank = 1),
        0
    )::int AS mention_medium,
    COALESCE(
        (SELECT COUNT(*) FROM with_overall WHERE mention_priority_rank = 2),
        0
    )::int AS mention_low,
    COALESCE(
        (
            SELECT ROUND(
                GREATEST(
                    0,
                    (1 - SUM(brand_gap_rate)::numeric / NULLIF(COUNT(*), 0)) * 100
                )::numeric,
                1
            )
            FROM with_overall
            WHERE brand_gap_rate > 0
        ),
        0
    )::float AS brand_gap_health,
    COALESCE(
        (SELECT COUNT(*) FROM with_overall WHERE brand_gap_rate > 0 AND brand_gap_priority_rank = 0),
        0
    )::int AS brand_gap_high,
    COALESCE(
        (SELECT COUNT(*) FROM with_overall WHERE brand_gap_rate > 0 AND brand_gap_priority_rank = 1),
        0
    )::int AS brand_gap_medium,
    COALESCE(
        (SELECT COUNT(*) FROM with_overall WHERE brand_gap_rate > 0 AND brand_gap_priority_rank = 2),
        0
    )::int AS brand_gap_low,
    COALESCE(
        (
            SELECT ROUND(
                GREATEST(
                    0,
                    (1 - SUM(source_gap_rate)::numeric / NULLIF(COUNT(*), 0)) * 100
                )::numeric,
                1
            )
            FROM with_overall
            WHERE source_gap_rate > 0
        ),
        0
    )::float AS source_gap_health,
    COALESCE(
        (SELECT COUNT(*) FROM with_overall WHERE source_gap_rate > 0 AND source_gap_priority_rank = 0),
        0
    )::int AS source_gap_high,
    COALESCE(
        (SELECT COUNT(*) FROM with_overall WHERE source_gap_rate > 0 AND source_gap_priority_rank = 1),
        0
    )::int AS source_gap_medium,
    COALESCE(
        (SELECT COUNT(*) FROM with_overall WHERE source_gap_rate > 0 AND source_gap_priority_rank = 2),
        0
    )::int AS source_gap_low
"""

_DEFAULT_ORDER = (
    "priority_rank ASC, mention_rate ASC, brand_gap_rate DESC, source_gap_rate DESC"
)
_SORT_COLUMNS = {
    "brand_gap_rate": "brand_gap_rate",
    "source_gap_rate": "source_gap_rate",
    "mention_rate": "mention_rate",
    "priority": "priority_rank",
}

_EMPTY_PRIORITY_COUNTS = {"high": 0, "medium": 0, "low": 0}


def _sql_bind_params(*, subject: Subject, dt_from: datetime, dt_to: datetime) -> dict[str, Any]:
    return {
        "subject_id": subject.id,
        "dt_from": dt_from,
        "dt_to": dt_to,
        "own_kind": EntityKind.own.value,
        "competitor_kind": EntityKind.competitor.value,
    }


def _order_clause(*, sort_by: str | None, order: str) -> str:
    if not sort_by:
        return _DEFAULT_ORDER
    column = _SORT_COLUMNS.get(sort_by)
    if column is None:
        return _DEFAULT_ORDER
    direction = "DESC" if order == "desc" else "ASC"
    return f"{column} {direction}, prompt_id ASC"


def _row_to_item(row: Any) -> dict[str, Any]:
    prompt_id = row.prompt_id
    mention_rate = float(row.mention_rate or 0)
    average_rank = float(row.average_rank) if row.average_rank is not None else None
    brand_gap_rate = float(row.brand_gap_rate or 0)
    source_gap_rate = float(row.source_gap_rate or 0)
    platforms = list(row.platforms or [])
    item = {
        "id": str(prompt_id),
        "prompt_id": str(prompt_id),
        "prompt_text": row.prompt_text,
        "platforms": platforms,
        "competitors": [],
        "brand_gap_rate": brand_gap_rate,
        "brand_gap_priority": gap_action_priority(brand_gap_rate),
        "source_gap_rate": source_gap_rate,
        "source_gap_priority": gap_action_priority(source_gap_rate),
        "brand_own_count": int(row.brand_own_count or 0),
        "brand_total_count": int(row.brand_total_count or 0),
        "source_own_count": int(row.source_own_count or 0),
        "source_total_count": int(row.source_total_count or 0),
        "mention_rate": mention_rate,
        "mention_own_count": int(row.mention_own_count or 0),
        "mention_total_count": int(row.mention_total_count or 0),
        "average_rank": average_rank,
    }
    item["mention_issue_type"] = diagnosis_issue_type(mention_rate, average_rank)
    item["mention_priority"] = mention_action_priority(mention_rate, average_rank)
    item["priority"] = overall_action_priority(
        item["mention_priority"],
        item["brand_gap_priority"],
        item["source_gap_priority"],
    )
    return item


def _summary_from_row(row: Any) -> dict[str, Any]:
    mention_count = int(row.mention_prompt_count or 0)
    gap_count = int(row.gap_prompt_count or 0)
    if mention_count == 0 and gap_count == 0:
        return {
            "overall_score": 0.0,
            "overall_status": "critical",
            "mention": {"health_score": 0.0, "priority_counts": dict(_EMPTY_PRIORITY_COUNTS)},
            "brand_gap": {"health_score": 0.0, "priority_counts": dict(_EMPTY_PRIORITY_COUNTS)},
            "source_gap": {"health_score": 0.0, "priority_counts": dict(_EMPTY_PRIORITY_COUNTS)},
        }

    mention_health = float(row.mention_health or 0)
    brand_gap_health = float(row.brand_gap_health or 0)
    source_gap_health = float(row.source_gap_health or 0)
    overall_score = round(mention_health * 0.4 + brand_gap_health * 0.3 + source_gap_health * 0.3, 1)
    return {
        "overall_score": overall_score,
        "overall_status": overall_diagnosis_status(overall_score),
        "mention": {
            "health_score": mention_health,
            "priority_counts": {
                "high": int(row.mention_high or 0),
                "medium": int(row.mention_medium or 0),
                "low": int(row.mention_low or 0),
            },
        },
        "brand_gap": {
            "health_score": brand_gap_health,
            "priority_counts": {
                "high": int(row.brand_gap_high or 0),
                "medium": int(row.brand_gap_medium or 0),
                "low": int(row.brand_gap_low or 0),
            },
        },
        "source_gap": {
            "health_score": source_gap_health,
            "priority_counts": {
                "high": int(row.source_gap_high or 0),
                "medium": int(row.source_gap_medium or 0),
                "low": int(row.source_gap_low or 0),
            },
        },
    }


def _attach_competitors(
    *,
    subject: Subject,
    focus_entity_id: str,
    items: list[dict[str, Any]],
    all_signals,
) -> None:
    if not items:
        return
    by_prompt: dict[UUID, list] = defaultdict(list)
    for row in all_signals:
        by_prompt[row.prompt_id].append(row)

    for item in items:
        prompt_id = UUID(item["prompt_id"])
        prompt_signals = by_prompt.get(prompt_id, [])
        entity_signals = [row for row in prompt_signals if row.entity_id == focus_entity_id]
        response_ids = {row.response_id for row in entity_signals}
        gap = _merged_diagnosis_gap_metrics(
            focus_entity_id=focus_entity_id,
            entity_signals=entity_signals,
            response_ids=response_ids,
            all_signals=prompt_signals,
            subject=subject,
        )
        item["competitors"] = gap["competitors"]


def _query_diagnosis_content_page(
    db: Session,
    *,
    subject: Subject,
    dt_from: datetime,
    dt_to: datetime,
    sort_by: str | None,
    order: str,
    page: int,
    page_size: int,
) -> tuple[list[dict[str, Any]], int]:
    entity = own_entity(subject)
    safe_page = max(1, page)
    safe_page_size = max(1, page_size)
    offset = (safe_page - 1) * safe_page_size
    sql = text(_DIAGNOSIS_CONTENT_PAGE_SQL.format(order_clause=_order_clause(sort_by=sort_by, order=order)))
    params = {
        **_sql_bind_params(subject=subject, dt_from=dt_from, dt_to=dt_to),
        "limit": safe_page_size,
        "offset": offset,
    }
    rows = db.execute(sql, params).all()

    if not rows:
        return [], 0

    total = int(rows[0].total_count or 0)
    items = [_row_to_item(row) for row in rows]
    prompt_ids = [UUID(item["prompt_id"]) for item in items]
    page_signals = load_llm_response_signals(
        db,
        subject=subject,
        dt_from=dt_from,
        dt_to=dt_to,
        prompt_ids=prompt_ids,
    )
    _attach_competitors(
        subject=subject,
        focus_entity_id=entity.id,
        items=items,
        all_signals=page_signals,
    )
    return items, total


def _query_diagnosis_content_summary(
    db: Session,
    *,
    subject: Subject,
    dt_from: datetime,
    dt_to: datetime,
) -> dict[str, Any]:
    row = db.execute(
        text(_DIAGNOSIS_CONTENT_SUMMARY_SQL),
        _sql_bind_params(subject=subject, dt_from=dt_from, dt_to=dt_to),
    ).one()
    return _summary_from_row(row)


class _QueryDiagnosisContentPage:
    """Patchable DB page query (tests may assign `.override`)."""

    override: Callable[..., tuple[list[dict[str, Any]], int]] | None = None

    def __call__(
        self,
        db: Session,
        *,
        subject: Subject,
        dt_from: datetime,
        dt_to: datetime,
        sort_by: str | None,
        order: str,
        page: int,
        page_size: int,
    ) -> tuple[list[dict[str, Any]], int]:
        if self.override is not None:
            return self.override(
                db,
                subject=subject,
                dt_from=dt_from,
                dt_to=dt_to,
                sort_by=sort_by,
                order=order,
                page=page,
                page_size=page_size,
            )
        return _query_diagnosis_content_page(
            db,
            subject=subject,
            dt_from=dt_from,
            dt_to=dt_to,
            sort_by=sort_by,
            order=order,
            page=page,
            page_size=page_size,
        )


class _QueryDiagnosisContentSummary:
    """Patchable DB summary query (tests may assign `.override`)."""

    override: Callable[..., dict[str, Any]] | None = None

    def __call__(
        self,
        db: Session,
        *,
        subject: Subject,
        dt_from: datetime,
        dt_to: datetime,
    ) -> dict[str, Any]:
        if self.override is not None:
            return self.override(
                db,
                subject=subject,
                dt_from=dt_from,
                dt_to=dt_to,
            )
        return _query_diagnosis_content_summary(
            db,
            subject=subject,
            dt_from=dt_from,
            dt_to=dt_to,
        )


query_diagnosis_content_page = _QueryDiagnosisContentPage()
query_diagnosis_content_summary = _QueryDiagnosisContentSummary()
