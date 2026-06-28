"""User in-app notification inbox."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "036_user_notifications"
down_revision: Union[str, None] = "035_usage_event_dedup"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TS = sa.DateTime(timezone=True)
_NOW = sa.text("now()")
_EPOCH = sa.text("'1970-01-01T00:00:00+00:00'::timestamptz")


def upgrade() -> None:
    op.create_table(
        "tb_user_notifications",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(as_uuid=True), sa.ForeignKey("tb_tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Uuid(as_uuid=True), sa.ForeignKey("tb_users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("category", sa.String(32), nullable=False),
        sa.Column("title", sa.String(128), nullable=False),
        sa.Column("body", sa.Text(), nullable=False, server_default=""),
        sa.Column("action_url", sa.String(512), nullable=False, server_default=""),
        sa.Column("read_at", _TS, nullable=False, server_default=_EPOCH),
        sa.Column("dedupe_key", sa.String(128), nullable=False, server_default=""),
        sa.Column("created_at", _TS, nullable=False, server_default=_NOW),
        sa.Column("updated_at", _TS, nullable=False, server_default=_NOW),
        sa.Column("deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.create_index(
        "ix_user_notifications_user_created",
        "tb_user_notifications",
        ["user_id", sa.text("created_at DESC")],
    )
    op.create_index(
        "ix_user_notifications_user_unread",
        "tb_user_notifications",
        ["user_id", "read_at"],
        postgresql_where=sa.text("read_at = '1970-01-01T00:00:00+00:00'::timestamptz AND deleted = false"),
    )
    op.create_index(
        "uq_user_notifications_dedupe",
        "tb_user_notifications",
        ["user_id", "dedupe_key"],
        unique=True,
        postgresql_where=sa.text("dedupe_key <> '' AND deleted = false"),
    )


def downgrade() -> None:
    op.drop_index("uq_user_notifications_dedupe", table_name="tb_user_notifications")
    op.drop_index("ix_user_notifications_user_unread", table_name="tb_user_notifications")
    op.drop_index("ix_user_notifications_user_created", table_name="tb_user_notifications")
    op.drop_table("tb_user_notifications")
