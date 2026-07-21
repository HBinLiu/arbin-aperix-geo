"""Drop unused decision_dimension from tb_subject_topics."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "050_drop_topic_decision_dim"
down_revision: Union[str, None] = "049_rename_prompt_decision_type"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col["name"] for col in inspector.get_columns("tb_subject_topics")}
    if "decision_dimension" in columns:
        op.drop_column("tb_subject_topics", "decision_dimension")


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col["name"] for col in inspector.get_columns("tb_subject_topics")}
    if "decision_dimension" not in columns:
        op.add_column(
            "tb_subject_topics",
            sa.Column(
                "decision_dimension",
                sa.String(length=32),
                nullable=False,
                server_default="",
            ),
        )
