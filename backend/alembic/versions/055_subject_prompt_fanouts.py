"""Create tb_subject_prompt_fanouts for materialized query fan-out candidates."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "055_subject_prompt_fanouts"
down_revision: Union[str, None] = "054_prompt_fanout_parent"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TS = sa.DateTime(timezone=True)
_NOW = sa.text("now()")
_ZERO = "00000000-0000-0000-0000-000000000000"
_EPOCH = "1970-01-01T00:00:00+00:00"


def upgrade() -> None:
    op.create_table(
        "tb_subject_prompt_fanouts",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("subject_id", sa.Uuid(), sa.ForeignKey("tb_subjects.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "parent_prompt_id",
            sa.Uuid(),
            sa.ForeignKey("tb_subject_prompts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "topic_id",
            sa.Uuid(),
            sa.ForeignKey("tb_subject_topics.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("query_text", sa.Text(), nullable=False, server_default=""),
        sa.Column("query_key", sa.Text(), nullable=False, server_default=""),
        sa.Column("frequency", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "platform_counts",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("first_seen_at", _TS, nullable=False, server_default=sa.text(f"'{_EPOCH}'")),
        sa.Column("last_seen_at", _TS, nullable=False, server_default=sa.text(f"'{_EPOCH}'")),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="pending"),
        sa.Column(
            "promoted_prompt_id",
            sa.Uuid(),
            nullable=False,
            server_default=sa.text(f"'{_ZERO}'"),
        ),
        sa.Column("created_at", _TS, nullable=False, server_default=_NOW),
        sa.Column("updated_at", _TS, nullable=False, server_default=_NOW),
        sa.Column("deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.create_index(
        "uq_subject_prompt_fanouts_parent_query",
        "tb_subject_prompt_fanouts",
        ["subject_id", "parent_prompt_id", "query_key"],
        unique=True,
        postgresql_where=sa.text("deleted = false"),
    )
    op.create_index(
        "ix_subject_prompt_fanouts_subject_status_freq",
        "tb_subject_prompt_fanouts",
        ["subject_id", "status", "frequency"],
    )
    op.create_index(
        "ix_subject_prompt_fanouts_subject_topic_status",
        "tb_subject_prompt_fanouts",
        ["subject_id", "topic_id", "status"],
    )
    op.create_index(
        "ix_subject_prompt_fanouts_last_seen_at",
        "tb_subject_prompt_fanouts",
        ["last_seen_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_subject_prompt_fanouts_last_seen_at", table_name="tb_subject_prompt_fanouts")
    op.drop_index("ix_subject_prompt_fanouts_subject_topic_status", table_name="tb_subject_prompt_fanouts")
    op.drop_index("ix_subject_prompt_fanouts_subject_status_freq", table_name="tb_subject_prompt_fanouts")
    op.drop_index("uq_subject_prompt_fanouts_parent_query", table_name="tb_subject_prompt_fanouts")
    op.drop_table("tb_subject_prompt_fanouts")
