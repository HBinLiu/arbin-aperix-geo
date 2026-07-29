"""Drop unused password column from tb_users (OTP-only auth)."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "059_drop_user_password"
down_revision: Union[str, None] = "058_doubao_login_tickets"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("tb_users", "password")


def downgrade() -> None:
    op.add_column(
        "tb_users",
        sa.Column("password", sa.String(255), nullable=False, server_default=""),
    )
