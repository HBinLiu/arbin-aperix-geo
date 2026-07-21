"""Add sampling_enabled flag to subjects for pause/resume monitoring."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "053_subject_sampling_enabled"
down_revision: Union[str, None] = "052_citation_url_type"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "tb_subjects",
        sa.Column(
            "sampling_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
    )


def downgrade() -> None:
    op.drop_column("tb_subjects", "sampling_enabled")
