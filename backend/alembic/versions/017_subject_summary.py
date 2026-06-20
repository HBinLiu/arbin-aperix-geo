"""Add summary column to tb_subjects."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "017_subject_summary"
down_revision: Union[str, None] = "016_sentiment_score_zero_default"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "tb_subjects",
        sa.Column("summary", sa.Text(), nullable=False, server_default=""),
    )


def downgrade() -> None:
    op.drop_column("tb_subjects", "summary")
