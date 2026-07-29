"""Create tb_doubao_login_tickets for Doubao Web re-login ops flow."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "058_doubao_login_tickets"
down_revision: Union[str, None] = "057_doubao_accounts"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TS = sa.DateTime(timezone=True)
_NOW = sa.text("now()")
_EPOCH = "1970-01-01T00:00:00+00:00"
_ZERO = "00000000-0000-0000-0000-000000000000"


def upgrade() -> None:
    op.create_table(
        "tb_doubao_login_tickets",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column(
            "account_id",
            sa.Uuid(),
            nullable=False,
            server_default=sa.text(f"'{_ZERO}'"),
        ),
        sa.Column("label", sa.String(length=128), nullable=False, server_default=""),
        sa.Column("token", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("operator", sa.String(length=128), nullable=False, server_default=""),
        sa.Column("login_url", sa.Text(), nullable=False, server_default=""),
        sa.Column("container_id", sa.String(length=128), nullable=False, server_default=""),
        sa.Column("expires_at", _TS, nullable=False, server_default=sa.text(f"'{_EPOCH}'")),
        sa.Column("completed_at", _TS, nullable=False, server_default=sa.text(f"'{_EPOCH}'")),
        sa.Column("error_text", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", _TS, nullable=False, server_default=_NOW),
        sa.Column("updated_at", _TS, nullable=False, server_default=_NOW),
        sa.Column("deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.create_index(
        "uq_doubao_login_tickets_token",
        "tb_doubao_login_tickets",
        ["token"],
        unique=True,
        postgresql_where=sa.text("deleted = false AND token <> ''"),
    )
    op.create_index(
        "ix_doubao_login_tickets_status_expires",
        "tb_doubao_login_tickets",
        ["status", "expires_at"],
        postgresql_where=sa.text("deleted = false"),
    )
    op.create_index(
        "ix_doubao_login_tickets_account_id",
        "tb_doubao_login_tickets",
        ["account_id"],
        postgresql_where=sa.text("deleted = false"),
    )


def downgrade() -> None:
    op.drop_index("ix_doubao_login_tickets_account_id", table_name="tb_doubao_login_tickets")
    op.drop_index("ix_doubao_login_tickets_status_expires", table_name="tb_doubao_login_tickets")
    op.drop_index("uq_doubao_login_tickets_token", table_name="tb_doubao_login_tickets")
    op.drop_table("tb_doubao_login_tickets")
