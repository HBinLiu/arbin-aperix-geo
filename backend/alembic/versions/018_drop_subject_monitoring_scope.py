"""Drop monitoring_scope from tb_subjects."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "018_drop_monitoring_scope"
down_revision: Union[str, None] = "017_subject_summary"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("tb_subjects", "monitoring_scope")


def downgrade() -> None:
    op.add_column(
        "tb_subjects",
        sa.Column(
            "monitoring_scope",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
