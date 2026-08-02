"""Bind sampling job quota reservations to a usage period."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "062_sampling_quota_period_id"
down_revision: Union[str, None] = "061_sampling_quota_reserve"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_ZERO = "00000000-0000-0000-0000-000000000000"


def upgrade() -> None:
    op.add_column(
        "tb_sampling_jobs",
        sa.Column(
            "quota_usage_period_id",
            sa.Uuid(),
            nullable=False,
            server_default=sa.text(f"'{_ZERO}'"),
        ),
    )


def downgrade() -> None:
    op.drop_column("tb_sampling_jobs", "quota_usage_period_id")
