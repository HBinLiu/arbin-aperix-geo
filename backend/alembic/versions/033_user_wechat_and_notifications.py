"""Add WeChat profile and notification settings to tb_users."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "033_user_wechat_notifications"
down_revision: Union[str, None] = "032_rename_domain_brand_uq"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "tb_users",
        sa.Column("nick_name", sa.String(128), nullable=False, server_default=""),
    )
    op.add_column(
        "tb_users",
        sa.Column("open_id", sa.String(128), nullable=False, server_default=""),
    )
    op.add_column(
        "tb_users",
        sa.Column("union_id", sa.String(128), nullable=False, server_default=""),
    )
    op.add_column(
        "tb_users",
        sa.Column("notify_in_app", sa.Boolean(), nullable=False, server_default="true"),
    )
    op.add_column(
        "tb_users",
        sa.Column("notify_email", sa.Boolean(), nullable=False, server_default="true"),
    )
    op.add_column(
        "tb_users",
        sa.Column("notify_wechat", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.create_index(
        "uq_users_wechat_open_id",
        "tb_users",
        ["open_id"],
        unique=True,
        postgresql_where=sa.text("open_id <> '' AND deleted = false"),
    )
    op.create_index(
        "uq_users_wechat_union_id",
        "tb_users",
        ["union_id"],
        unique=True,
        postgresql_where=sa.text("union_id <> '' AND deleted = false"),
    )


def downgrade() -> None:
    op.drop_index("uq_users_wechat_union_id", table_name="tb_users")
    op.drop_index("uq_users_wechat_open_id", table_name="tb_users")
    op.drop_column("tb_users", "notify_wechat")
    op.drop_column("tb_users", "notify_email")
    op.drop_column("tb_users", "notify_in_app")
    op.drop_column("tb_users", "union_id")
    op.drop_column("tb_users", "open_id")
    op.drop_column("tb_users", "nick_name")
