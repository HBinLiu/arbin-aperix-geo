"""Rename tb_subject_prompts.decision_dimension to decision_type."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "049_rename_prompt_decision_type"
down_revision: Union[str, None] = "048_prompt_decision_dimension"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TABLE = "tb_subject_prompts"
_OLD = "decision_dimension"
_NEW = "decision_type"


def _column_names(conn, table: str) -> set[str]:
    return {col["name"] for col in inspect(conn).get_columns(table)}


def upgrade() -> None:
    conn = op.get_bind()
    columns = _column_names(conn, _TABLE)

    if _NEW in columns:
        if _OLD in columns:
            op.execute(
                sa.text(
                    f"UPDATE {_TABLE} SET {_NEW} = {_OLD} "
                    f"WHERE {_NEW} = '' AND {_OLD} <> ''"
                )
            )
            op.drop_column(_TABLE, _OLD)
        return

    if _OLD in columns:
        op.alter_column(_TABLE, _OLD, new_column_name=_NEW, existing_type=sa.String(length=32))
        return

    op.add_column(
        _TABLE,
        sa.Column(_NEW, sa.String(length=32), nullable=False, server_default=""),
    )


def downgrade() -> None:
    conn = op.get_bind()
    columns = _column_names(conn, _TABLE)

    if _OLD in columns:
        if _NEW in columns:
            op.drop_column(_TABLE, _NEW)
        return

    if _NEW in columns:
        op.alter_column(_TABLE, _NEW, new_column_name=_OLD, existing_type=sa.String(length=32))
        return
