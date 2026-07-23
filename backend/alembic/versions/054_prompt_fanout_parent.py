"""Add parent_prompt_id / kind / origin_query for query fan-out prompts."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "054_prompt_fanout_parent"
down_revision: Union[str, None] = "053_subject_sampling_enabled"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_ZERO = "00000000-0000-0000-0000-000000000000"


def upgrade() -> None:
    op.add_column(
        "tb_subject_prompts",
        sa.Column(
            "parent_prompt_id",
            sa.Uuid(),
            nullable=False,
            server_default=sa.text(f"'{_ZERO}'"),
        ),
    )
    op.add_column(
        "tb_subject_prompts",
        sa.Column(
            "kind",
            sa.String(length=16),
            nullable=False,
            server_default="root",
        ),
    )
    op.add_column(
        "tb_subject_prompts",
        sa.Column(
            "origin_query",
            sa.Text(),
            nullable=False,
            server_default="",
        ),
    )
    op.create_index(
        "ix_subject_prompts_parent_prompt_id",
        "tb_subject_prompts",
        ["parent_prompt_id"],
    )
    op.create_index(
        "ix_subject_prompts_subject_kind",
        "tb_subject_prompts",
        ["subject_id", "kind"],
    )


def downgrade() -> None:
    op.drop_index("ix_subject_prompts_subject_kind", table_name="tb_subject_prompts")
    op.drop_index("ix_subject_prompts_parent_prompt_id", table_name="tb_subject_prompts")
    op.drop_column("tb_subject_prompts", "origin_query")
    op.drop_column("tb_subject_prompts", "kind")
    op.drop_column("tb_subject_prompts", "parent_prompt_id")
