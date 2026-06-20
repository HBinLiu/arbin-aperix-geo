"""Signal table: add sentiment_reason, drop sentiment_label."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "015_signal_schema_refactor"
down_revision: Union[str, None] = "014_drop_sampling_interval"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TABLE = "tb_llm_response_signals"


def _column_names(conn) -> set[str]:
    return {col["name"] for col in inspect(conn).get_columns(_TABLE)}


def _unique_constraint_columns(conn) -> list[list[str]]:
    return [uq["column_names"] for uq in inspect(conn).get_unique_constraints(_TABLE)]


def _index_names(conn) -> set[str]:
    return {idx["name"] for idx in inspect(conn).get_indexes(_TABLE)}


def _backfill_required_signal_fields() -> None:
    op.execute(
        sa.text(
            f"UPDATE {_TABLE} "
            "SET mention_rank = 0 "
            "WHERE mention_rank < 0"
        )
    )
    op.execute(
        sa.text(
            f"UPDATE {_TABLE} "
            "SET sentiment_score = -1 "
            "WHERE sentiment_score < 0"
        )
    )
    op.execute(
        sa.text(
            f"UPDATE {_TABLE} "
            "SET sentiment_score = -1, sentiment_reason = '' "
            "WHERE mentioned = false"
        )
    )


def _ensure_entity_unique_key(conn) -> None:
    """Keep uq_llm_response_signal on (response_id, entity_id)."""
    unique_cols = _unique_constraint_columns(conn)
    if ["response_id", "entity_id"] in unique_cols:
        return

    if ["response_id", "brand_id"] in unique_cols:
        op.drop_constraint("uq_llm_response_signal", _TABLE, type_="unique")

    op.create_unique_constraint(
        "uq_llm_response_signal",
        _TABLE,
        ["response_id", "entity_id"],
    )


def _ensure_entity_indexes(conn) -> None:
    index_names = _index_names(conn)
    if "ix_llm_response_signals_subject_brand_created" in index_names:
        op.drop_index("ix_llm_response_signals_subject_brand_created", table_name=_TABLE)
    if "ix_llm_response_signals_subject_prompt_brand" in index_names:
        op.drop_index("ix_llm_response_signals_subject_prompt_brand", table_name=_TABLE)

    index_names = _index_names(conn)
    if "ix_llm_response_signals_subject_entity_created" not in index_names:
        op.create_index(
            "ix_llm_response_signals_subject_entity_created",
            _TABLE,
            ["subject_id", "entity_id", "created_at"],
        )
    if "ix_llm_response_signals_subject_prompt_entity" not in index_names:
        op.create_index(
            "ix_llm_response_signals_subject_prompt_entity",
            _TABLE,
            ["subject_id", "prompt_id", "entity_id"],
        )


def upgrade() -> None:
    conn = op.get_bind()
    columns = _column_names(conn)

    if "sentiment_reason" not in columns:
        op.add_column(
            _TABLE,
            sa.Column("sentiment_reason", sa.Text(), nullable=False, server_default=""),
        )

    _backfill_required_signal_fields()

    if "sentiment_label" in _column_names(conn):
        op.drop_column(_TABLE, "sentiment_label")

    _ensure_entity_unique_key(conn)
    _ensure_entity_indexes(conn)


def downgrade() -> None:
    conn = op.get_bind()
    columns = _column_names(conn)

    index_names = _index_names(conn)
    if "ix_llm_response_signals_subject_entity_created" in index_names:
        op.drop_index("ix_llm_response_signals_subject_entity_created", table_name=_TABLE)
    if "ix_llm_response_signals_subject_prompt_entity" in index_names:
        op.drop_index("ix_llm_response_signals_subject_prompt_entity", table_name=_TABLE)

    if "sentiment_label" not in columns:
        op.add_column(
            _TABLE,
            sa.Column("sentiment_label", sa.String(16), nullable=True),
        )
        op.execute(sa.text(f"UPDATE {_TABLE} SET sentiment_label = 'neutral'"))
        op.alter_column(
            _TABLE,
            "sentiment_label",
            existing_type=sa.String(16),
            nullable=False,
            server_default="neutral",
        )

    if "sentiment_reason" in columns:
        op.drop_column(_TABLE, "sentiment_reason")
