"""Add site_name to domain profiles for citation/backlink display."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "063_domain_profile_site_name"
down_revision: Union[str, None] = "062_sampling_quota_period_id"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "tb_domain_profiles",
        sa.Column("site_name", sa.String(length=255), nullable=False, server_default=""),
    )


def downgrade() -> None:
    op.drop_column("tb_domain_profiles", "site_name")
