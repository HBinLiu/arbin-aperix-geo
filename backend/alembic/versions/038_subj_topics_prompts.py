"""Rename tb_topics/tb_prompts to tb_subject_topics/tb_subject_prompts."""

from typing import Sequence, Union

from alembic import op

revision: str = "038_subj_topics_prompts"
down_revision: Union[str, None] = "037_plan_packs_rename"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_INDEX_RENAMES = (
    ("ix_topics_subject_id", "ix_subject_topics_subject_id"),
    ("ix_prompts_subject_id", "ix_subject_prompts_subject_id"),
    ("ix_prompts_topic_id", "ix_subject_prompts_topic_id"),
    ("uq_subject_prompt_hash", "uq_subject_prompts_hash"),
)


def upgrade() -> None:
    op.rename_table("tb_topics", "tb_subject_topics")
    op.rename_table("tb_prompts", "tb_subject_prompts")
    for old, new in _INDEX_RENAMES:
        op.execute(f'ALTER INDEX IF EXISTS "{old}" RENAME TO "{new}"')


def downgrade() -> None:
    for old, new in _INDEX_RENAMES:
        op.execute(f'ALTER INDEX IF EXISTS "{new}" RENAME TO "{old}"')
    op.rename_table("tb_subject_prompts", "tb_prompts")
    op.rename_table("tb_subject_topics", "tb_topics")
