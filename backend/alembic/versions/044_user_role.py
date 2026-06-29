"""Add role column to tb_users for tenant member permissions."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "044_user_role"
down_revision: Union[str, None] = "043_usage_pack_purchase_type"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "tb_users",
        sa.Column("role", sa.String(32), nullable=False, server_default="admin"),
    )


def downgrade() -> None:
    op.drop_column("tb_users", "role")
