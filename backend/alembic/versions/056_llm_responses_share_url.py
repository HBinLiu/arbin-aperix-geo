"""Add share_url column to tb_llm_responses for Doubao crawl evidence."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "056_llm_responses_share_url"
down_revision: Union[str, None] = "055_subject_prompt_fanouts"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "tb_llm_responses",
        sa.Column("share_url", sa.Text(), nullable=False, server_default=""),
    )


def downgrade() -> None:
    op.drop_column("tb_llm_responses", "share_url")
