"""Add decision_dimension to tb_subject_topics."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "047_topic_decision_dimension"
down_revision: Union[str, None] = "046_knowledge_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "tb_subject_topics",
        sa.Column(
            "decision_dimension",
            sa.String(length=32),
            nullable=False,
            server_default="",
        ),
    )


def downgrade() -> None:
    op.drop_column("tb_subject_topics", "decision_dimension")
