"""Add tb_llm_response_signals analytical fact table."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "012_llm_response_signals"
down_revision: Union[str, None] = "011_competitor_aliases"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "tb_llm_response_signals",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("response_id", sa.Uuid(), nullable=False),
        sa.Column("subject_id", sa.Uuid(), nullable=False),
        sa.Column("prompt_id", sa.Uuid(), nullable=False),
        sa.Column("platform", sa.String(length=128), nullable=False, server_default=""),
        sa.Column("entity_id", sa.String(length=64), nullable=False),
        sa.Column("entity_kind", sa.String(length=16), nullable=False),
        sa.Column("mentioned", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("mention_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("mention_rank", sa.Integer(), nullable=True),
        sa.Column("sentiment_score", sa.Float(), nullable=True),
        sa.Column("sentiment_label", sa.String(length=16), nullable=False, server_default="neutral"),
        sa.Column("has_domain_link", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("cited_on_source", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["response_id"], ["tb_llm_responses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["subject_id"], ["tb_subjects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["prompt_id"], ["tb_prompts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("response_id", "entity_id", name="uq_llm_response_signal"),
    )
    op.create_index(
        "ix_llm_response_signals_subject_entity_created",
        "tb_llm_response_signals",
        ["subject_id", "entity_id", "created_at"],
    )
    op.create_index(
        "ix_llm_response_signals_subject_prompt_entity",
        "tb_llm_response_signals",
        ["subject_id", "prompt_id", "entity_id"],
    )
    op.create_index("ix_llm_response_signals_response_id", "tb_llm_response_signals", ["response_id"])


def downgrade() -> None:
    op.drop_index("ix_llm_response_signals_response_id", table_name="tb_llm_response_signals")
    op.drop_index("ix_llm_response_signals_subject_prompt_entity", table_name="tb_llm_response_signals")
    op.drop_index("ix_llm_response_signals_subject_entity_created", table_name="tb_llm_response_signals")
    op.drop_table("tb_llm_response_signals")
