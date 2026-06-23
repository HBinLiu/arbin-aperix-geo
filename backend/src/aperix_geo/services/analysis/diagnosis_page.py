"""DB-side pagination and summary aggregation for diagnosis content."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from aperix_geo.db.models import EntityKind, Prompt, Subject
from aperix_geo.services.analysis.diagnosis import (
    _lookup_entity_citation_urls,
    diagnosis_issue_type,
    gap_action_priority,
    mention_action_priority,
    overall_action_priority,
    overall_diagnosis_status,
)
from aperix_geo.services.analysis.entity import competitor_entities, list_analysis_entities

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
),
own_pool AS (
    SELECT DISTINCT prompt_id, response_id
    FROM scoped
    WHERE entity_kind = :own_kind
),
competitor_hits AS (
    SELECT DISTINCT
        s.prompt_id,
        s.entity_id,
        s.entity_label,
        COALESCE(
            array_position(CAST(:competitor_entity_ids AS text[]), s.entity_id),
            100000
        ) AS ord_key
    FROM scoped s
    INNER JOIN own_pool op
        ON op.prompt_id = s.prompt_id AND op.response_id = s.response_id
    WHERE s.entity_kind = :competitor_kind
      AND (s.mentioned OR s.has_domain_link)
      AND s.entity_label <> ''
),
prompt_competitors AS (
    SELECT
        prompt_id,
        ARRAY_AGG(entity_label ORDER BY ord_key, entity_label) AS competitors
    FROM competitor_hits
    GROUP BY prompt_id
)
"""

_GAP_ITEM_CTES = """
merged AS (
    SELECT
        p.id AS prompt_id,
        p.text AS prompt_text,
        COALESCE(gp.platforms, ARRAY[]::text[]) AS platforms,
        COALESCE(pc.competitors, ARRAY[]::text[]) AS competitors,
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
    LEFT JOIN prompt_competitors pc ON pc.prompt_id = p.id
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
        "competitor_entity_ids": [entity.id for entity in competitor_entities(subject)],
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
        "competitors": list(row.competitors or []),
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


_SCOPED_PROMPT_CTES = """
scoped AS (
    SELECT
        prompt_id,
        platform,
        response_id,
        entity_id,
        entity_kind,
        entity_label,
        mentioned,
        mention_count,
        mention_rank,
        has_domain_link
    FROM tb_llm_response_signals
    WHERE subject_id = :subject_id
      AND prompt_id = :prompt_id
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
    SELECT
        brand_gap_rate,
        brand_own_count,
        brand_total_count
    FROM platform_gap
    ORDER BY brand_gap_rate DESC, platform ASC
    LIMIT 1
),
source_max AS (
    SELECT
        source_gap_rate,
        source_own_count,
        source_total_count
    FROM platform_gap
    ORDER BY source_gap_rate DESC, platform ASC
    LIMIT 1
),
own_mention AS (
    SELECT
        COUNT(DISTINCT response_id) AS mention_total_count,
        COUNT(DISTINCT response_id) FILTER (WHERE mentioned) AS mention_own_count
    FROM scoped
    WHERE entity_kind = :own_kind
),
own_pool AS (
    SELECT DISTINCT response_id
    FROM scoped
    WHERE entity_kind = :own_kind
),
aggregates AS (
    SELECT
        COALESCE((SELECT brand_gap_rate FROM brand_max), 0)::float AS brand_gap_rate,
        COALESCE((SELECT brand_own_count FROM brand_max), 0)::int AS brand_own_count,
        COALESCE((SELECT brand_total_count FROM brand_max), 0)::int AS brand_total_count,
        COALESCE((SELECT source_gap_rate FROM source_max), 0)::float AS source_gap_rate,
        COALESCE((SELECT source_own_count FROM source_max), 0)::int AS source_own_count,
        COALESCE((SELECT source_total_count FROM source_max), 0)::int AS source_total_count,
        COALESCE((SELECT mention_own_count FROM own_mention), 0)::int AS chat_mention_own,
        COALESCE((SELECT mention_total_count FROM own_mention), 0)::int AS chat_mention_total,
        COALESCE(
            (
                SELECT COUNT(DISTINCT s.entity_id)
                FROM scoped s
                INNER JOIN own_pool op ON op.response_id = s.response_id
                WHERE s.entity_kind = :competitor_kind AND s.mentioned
            ),
            0
        )::int AS competitor_brand_count,
        COALESCE(
            (
                SELECT SUM(s.mention_count)
                FROM scoped s
                INNER JOIN own_pool op ON op.response_id = s.response_id
            ),
            0
        )::int AS total_mention_count,
        COALESCE(
            (
                SELECT COUNT(*)
                FROM scoped s
                INNER JOIN own_pool op ON op.response_id = s.response_id
                WHERE s.has_domain_link
            ),
            0
        )::int AS total_source_count
    FROM (SELECT 1) AS _one
)
"""

_DIAGNOSIS_DETAIL_SUMMARY_SQL = f"WITH {_SCOPED_PROMPT_CTES} SELECT * FROM aggregates"

_DIAGNOSIS_DETAIL_BRAND_BREAKDOWN_SQL = f"""
WITH {_SCOPED_PROMPT_CTES},
brand_gap_platforms AS (
    SELECT platform
    FROM platform_gap
    WHERE brand_gap_rate > 0
),
gap_pool AS (
    SELECT rf.response_id, rf.platform
    FROM response_flags rf
    WHERE rf.platform IN (SELECT platform FROM brand_gap_platforms)
),
per_platform AS (
    SELECT
        s.entity_id,
        s.platform,
        COUNT(DISTINCT s.response_id) AS response_count,
        CASE
            WHEN COUNT(DISTINCT s.response_id) > 0 THEN ROUND(
                COUNT(DISTINCT s.response_id) FILTER (WHERE s.mentioned)::numeric
                    / COUNT(DISTINCT s.response_id),
                4
            )
            ELSE 0
        END AS visibility_rate,
        ROUND(
            AVG(s.mention_rank) FILTER (WHERE s.mentioned AND s.mention_rank > 0),
            2
        ) AS average_rank
    FROM scoped s
    INNER JOIN gap_pool gp
        ON gp.response_id = s.response_id AND gp.platform = s.platform
    WHERE s.entity_kind = :competitor_kind
    GROUP BY s.entity_id, s.platform
),
entity_roll AS (
    SELECT
        s.entity_id,
        CASE
            WHEN COUNT(DISTINCT s.response_id) > 0 THEN ROUND(
                COUNT(DISTINCT s.response_id) FILTER (WHERE s.mentioned)::numeric
                    / COUNT(DISTINCT s.response_id),
                4
            )
            ELSE 0
        END AS contribution_rate,
        ROUND(
            AVG(s.mention_rank) FILTER (WHERE s.mentioned AND s.mention_rank > 0),
            2
        ) AS average_rank
    FROM scoped s
    INNER JOIN gap_pool gp
        ON gp.response_id = s.response_id AND gp.platform = s.platform
    WHERE s.entity_kind = :competitor_kind
    GROUP BY s.entity_id
)
SELECT
    er.entity_id,
    er.contribution_rate,
    er.average_rank,
    COALESCE(
        ARRAY_AGG(DISTINCT pp.platform ORDER BY pp.platform)
            FILTER (WHERE pp.visibility_rate > 0),
        ARRAY[]::text[]
    ) AS platforms
FROM entity_roll er
LEFT JOIN per_platform pp ON pp.entity_id = er.entity_id
WHERE er.contribution_rate > 0
GROUP BY er.entity_id, er.contribution_rate, er.average_rank
ORDER BY
    er.average_rank ASC NULLS LAST,
    er.contribution_rate DESC,
    er.entity_id ASC
"""

_DIAGNOSIS_DETAIL_SOURCE_BREAKDOWN_SQL = f"""
WITH {_SCOPED_PROMPT_CTES},
source_gap_platforms AS (
    SELECT platform
    FROM platform_gap
    WHERE source_gap_rate > 0
),
gap_pool AS (
    SELECT rf.response_id, rf.platform
    FROM response_flags rf
    WHERE rf.platform IN (SELECT platform FROM source_gap_platforms)
),
per_platform AS (
    SELECT
        s.entity_id,
        s.platform,
        CASE
            WHEN COUNT(DISTINCT s.response_id) > 0 THEN ROUND(
                COUNT(*) FILTER (WHERE s.has_domain_link)::numeric
                    / COUNT(DISTINCT s.response_id),
                4
            )
            ELSE 0
        END AS link_rate
    FROM scoped s
    INNER JOIN gap_pool gp
        ON gp.response_id = s.response_id AND gp.platform = s.platform
    WHERE s.entity_kind = :competitor_kind
    GROUP BY s.entity_id, s.platform
),
entity_roll AS (
    SELECT
        s.entity_id,
        CASE
            WHEN COUNT(DISTINCT s.response_id) > 0 THEN ROUND(
                COUNT(*) FILTER (WHERE s.has_domain_link)::numeric
                    / COUNT(DISTINCT s.response_id),
                4
            )
            ELSE 0
        END AS contribution_rate
    FROM scoped s
    INNER JOIN gap_pool gp
        ON gp.response_id = s.response_id AND gp.platform = s.platform
    WHERE s.entity_kind = :competitor_kind
    GROUP BY s.entity_id
),
linked_responses AS (
    SELECT DISTINCT s.entity_id, s.response_id
    FROM scoped s
    INNER JOIN gap_pool gp
        ON gp.response_id = s.response_id AND gp.platform = s.platform
    WHERE s.entity_kind = :competitor_kind AND s.has_domain_link
)
SELECT
    er.entity_id,
    er.contribution_rate,
    COALESCE(
        ARRAY_AGG(DISTINCT pp.platform ORDER BY pp.platform)
            FILTER (WHERE pp.link_rate > 0),
        ARRAY[]::text[]
    ) AS platforms,
    ARRAY_AGG(DISTINCT lr.response_id) FILTER (WHERE lr.response_id IS NOT NULL) AS linked_response_ids
FROM entity_roll er
LEFT JOIN per_platform pp ON pp.entity_id = er.entity_id
LEFT JOIN linked_responses lr ON lr.entity_id = er.entity_id
WHERE er.contribution_rate > 0
GROUP BY er.entity_id, er.contribution_rate
ORDER BY er.contribution_rate DESC, er.entity_id ASC
"""

_DIAGNOSIS_DETAIL_LINKED_ENTITIES_SQL = f"""
WITH {_SCOPED_PROMPT_CTES},
own_pool AS (
    SELECT DISTINCT response_id
    FROM scoped
    WHERE entity_kind = :own_kind
)
SELECT DISTINCT s.entity_id
FROM scoped s
INNER JOIN own_pool op ON op.response_id = s.response_id
WHERE s.entity_kind = :competitor_kind AND s.has_domain_link
"""


def _detail_bind_params(
    *,
    subject: Subject,
    prompt_id: UUID,
    dt_from: datetime,
    dt_to: datetime,
) -> dict[str, Any]:
    return {
        "subject_id": subject.id,
        "prompt_id": prompt_id,
        "dt_from": dt_from,
        "dt_to": dt_to,
        "own_kind": EntityKind.own.value,
        "competitor_kind": EntityKind.competitor.value,
    }


def _entity_catalog(subject: Subject) -> dict[str, Any]:
    return {entity.id: entity for entity in list_analysis_entities(subject)}


def _competitor_source_domain_count(
    *,
    subject: Subject,
    linked_entity_ids: list[str],
) -> int:
    competitor_ids = {entity.id for entity in competitor_entities(subject)}
    seen: set[str] = set()
    catalog = _entity_catalog(subject)
    for entity_id in linked_entity_ids:
        if entity_id not in competitor_ids:
            continue
        entity = catalog.get(entity_id)
        if entity is None:
            continue
        key = (entity.domain or entity.label).strip().lower()
        if key:
            seen.add(key)
    return len(seen)


def _brand_breakdown_rows(
    rows: list[Any],
    *,
    subject: Subject,
) -> list[dict[str, Any]]:
    catalog = _entity_catalog(subject)
    out: list[dict[str, Any]] = []
    for row in rows:
        entity = catalog.get(str(row.entity_id))
        if entity is None:
            continue
        out.append(
            {
                "entity_id": entity.id,
                "label": entity.label,
                "display_name": entity.display_name,
                "domain": entity.domain or None,
                "platforms": list(row.platforms or []),
                "contribution_rate": float(row.contribution_rate or 0),
                "average_rank": float(row.average_rank) if row.average_rank is not None else None,
            }
        )
    return out


def _source_breakdown_rows(
    db: Session,
    rows: list[Any],
    *,
    subject: Subject,
) -> list[dict[str, Any]]:
    catalog = _entity_catalog(subject)
    out: list[dict[str, Any]] = []
    for row in rows:
        entity = catalog.get(str(row.entity_id))
        if entity is None:
            continue
        linked_response_ids = {item for item in (row.linked_response_ids or []) if item is not None}
        out.append(
            {
                "entity_id": entity.id,
                "label": entity.label,
                "display_name": entity.display_name,
                "domain": entity.domain or None,
                "platforms": list(row.platforms or []),
                "contribution_rate": float(row.contribution_rate or 0),
                "average_rank": None,
                "citation_urls": _lookup_entity_citation_urls(
                    db,
                    response_ids=linked_response_ids,
                    domain=entity.domain,
                    label=entity.label,
                ),
            }
        )
    return out


def _query_diagnosis_content_detail(
    db: Session,
    *,
    subject: Subject,
    prompt: Prompt,
    dt_from: datetime,
    dt_to: datetime,
) -> dict[str, Any]:
    params = _detail_bind_params(
        subject=subject,
        prompt_id=prompt.id,
        dt_from=dt_from,
        dt_to=dt_to,
    )
    summary = db.execute(text(_DIAGNOSIS_DETAIL_SUMMARY_SQL), params).one()
    brand_gap_rate = float(summary.brand_gap_rate or 0)
    source_gap_rate = float(summary.source_gap_rate or 0)

    brand_rows = _brand_breakdown_rows(
        db.execute(text(_DIAGNOSIS_DETAIL_BRAND_BREAKDOWN_SQL), params).all(),
        subject=subject,
    )
    source_rows = _source_breakdown_rows(
        db,
        db.execute(text(_DIAGNOSIS_DETAIL_SOURCE_BREAKDOWN_SQL), params).all(),
        subject=subject,
    )
    linked_entity_ids = [
        str(row.entity_id)
        for row in db.execute(text(_DIAGNOSIS_DETAIL_LINKED_ENTITIES_SQL), params).all()
    ]

    return {
        "prompt_id": str(prompt.id),
        "prompt_text": prompt.text,
        "brand": {
            "gap_rate": brand_gap_rate,
            "gap_priority": gap_action_priority(brand_gap_rate),
            "chat_mention_own": int(summary.chat_mention_own or 0),
            "chat_mention_total": int(summary.chat_mention_total or 0),
            "competitor_brand_count": int(summary.competitor_brand_count or 0),
            "total_mention_count": int(summary.total_mention_count or 0),
            "rows": brand_rows,
        },
        "source": {
            "gap_rate": source_gap_rate,
            "gap_priority": gap_action_priority(source_gap_rate),
            "chat_source_own": int(summary.source_own_count or 0),
            "chat_source_total": int(summary.source_total_count or 0),
            "competitor_source_count": _competitor_source_domain_count(
                subject=subject,
                linked_entity_ids=linked_entity_ids,
            ),
            "total_source_count": int(summary.total_source_count or 0),
            "rows": source_rows,
        },
    }


class _QueryDiagnosisContentDetail:
    """Patchable DB detail query (tests may assign `.override`)."""

    override: Callable[..., dict[str, Any]] | None = None

    def __call__(
        self,
        db: Session,
        *,
        subject: Subject,
        prompt: Prompt,
        dt_from: datetime,
        dt_to: datetime,
    ) -> dict[str, Any]:
        if self.override is not None:
            return self.override(
                db,
                subject=subject,
                prompt=prompt,
                dt_from=dt_from,
                dt_to=dt_to,
            )
        return _query_diagnosis_content_detail(
            db,
            subject=subject,
            prompt=prompt,
            dt_from=dt_from,
            dt_to=dt_to,
        )


query_diagnosis_content_detail = _QueryDiagnosisContentDetail()
