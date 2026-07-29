"""Create tb_doubao_accounts for global Doubao Web crawl account pool."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "057_doubao_accounts"
down_revision: Union[str, None] = "056_llm_responses_share_url"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TS = sa.DateTime(timezone=True)
_NOW = sa.text("now()")
_EPOCH = "1970-01-01T00:00:00+00:00"


def upgrade() -> None:
    op.create_table(
        "tb_doubao_accounts",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("label", sa.String(length=128), nullable=False, server_default=""),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
        sa.Column(
            "storage_state",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("last_ok_at", _TS, nullable=False, server_default=sa.text(f"'{_EPOCH}'")),
        sa.Column("last_error", sa.Text(), nullable=False, server_default=""),
        sa.Column("lease_owner", sa.String(length=128), nullable=False, server_default=""),
        sa.Column("lease_until", _TS, nullable=False, server_default=sa.text(f"'{_EPOCH}'")),
        sa.Column("created_at", _TS, nullable=False, server_default=_NOW),
        sa.Column("updated_at", _TS, nullable=False, server_default=_NOW),
        sa.Column("deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.create_index(
        "uq_doubao_accounts_label",
        "tb_doubao_accounts",
        ["label"],
        unique=True,
        postgresql_where=sa.text("deleted = false AND label <> ''"),
    )
    op.create_index(
        "ix_doubao_accounts_status_last_ok",
        "tb_doubao_accounts",
        ["status", "last_ok_at"],
        postgresql_where=sa.text("deleted = false"),
    )


def downgrade() -> None:
    op.drop_index("ix_doubao_accounts_status_last_ok", table_name="tb_doubao_accounts")
    op.drop_index("uq_doubao_accounts_label", table_name="tb_doubao_accounts")
    op.drop_table("tb_doubao_accounts")
