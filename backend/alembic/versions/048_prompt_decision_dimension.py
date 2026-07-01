"""Add decision_type to tb_subject_prompts."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "048_prompt_decision_dimension"
down_revision: Union[str, None] = "047_topic_decision_dimension"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "tb_subject_prompts",
        sa.Column(
            "decision_type",
            sa.String(length=32),
            nullable=False,
            server_default="",
        ),
    )


def downgrade() -> None:
    op.drop_column("tb_subject_prompts", "decision_type")
