"""Drop per-subject sampling_interval; daily schedule is system-wide."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "014_drop_sampling_interval"
down_revision: Union[str, None] = "001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(sa.text("ALTER TABLE tb_subjects DROP CONSTRAINT IF EXISTS ck_tb_subjects_sampling_interval"))
    op.drop_column("tb_subjects", "sampling_interval")


def downgrade() -> None:
    op.add_column(
        "tb_subjects",
        sa.Column("sampling_interval", sa.Integer(), nullable=False, server_default="24"),
    )
    op.execute(
        sa.text(
            "ALTER TABLE tb_subjects ADD CONSTRAINT ck_tb_subjects_sampling_interval "
            "CHECK (sampling_interval IN (0, 6, 12, 24, 72, 168))"
        )
    )
