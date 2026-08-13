"""Rename Doubao crawl account tables to tb_crawl_* and add platform column."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "065_crawl_accounts_platform"
down_revision: Union[str, None] = "064_drop_comp_cross_validate"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- accounts ---
    op.drop_index("ix_doubao_accounts_status_last_ok", table_name="tb_doubao_accounts")
    op.drop_index("uq_doubao_accounts_label", table_name="tb_doubao_accounts")
    op.rename_table("tb_doubao_accounts", "tb_crawl_accounts")
    op.add_column(
        "tb_crawl_accounts",
        sa.Column(
            "platform",
            sa.String(length=32),
            nullable=False,
            server_default="doubao",
        ),
    )
    op.create_index(
        "uq_crawl_accounts_platform_label",
        "tb_crawl_accounts",
        ["platform", "label"],
        unique=True,
        postgresql_where=sa.text("deleted = false AND label <> ''"),
    )
    op.create_index(
        "ix_crawl_accounts_platform_status_last_ok",
        "tb_crawl_accounts",
        ["platform", "status", "last_ok_at"],
        postgresql_where=sa.text("deleted = false"),
    )

    # --- tickets ---
    op.drop_index("ix_doubao_login_tickets_account_id", table_name="tb_doubao_login_tickets")
    op.drop_index("ix_doubao_login_tickets_status_expires", table_name="tb_doubao_login_tickets")
    op.drop_index("uq_doubao_login_tickets_token", table_name="tb_doubao_login_tickets")
    op.rename_table("tb_doubao_login_tickets", "tb_crawl_login_tickets")
    op.add_column(
        "tb_crawl_login_tickets",
        sa.Column(
            "platform",
            sa.String(length=32),
            nullable=False,
            server_default="doubao",
        ),
    )
    op.create_index(
        "uq_crawl_login_tickets_token",
        "tb_crawl_login_tickets",
        ["token"],
        unique=True,
        postgresql_where=sa.text("deleted = false AND token <> ''"),
    )
    op.create_index(
        "ix_crawl_login_tickets_status_expires",
        "tb_crawl_login_tickets",
        ["status", "expires_at"],
        postgresql_where=sa.text("deleted = false"),
    )
    op.create_index(
        "ix_crawl_login_tickets_account_id",
        "tb_crawl_login_tickets",
        ["account_id"],
        postgresql_where=sa.text("deleted = false"),
    )
    op.create_index(
        "ix_crawl_login_tickets_platform_status",
        "tb_crawl_login_tickets",
        ["platform", "status"],
        postgresql_where=sa.text("deleted = false"),
    )


def downgrade() -> None:
    op.drop_index(
        "ix_crawl_login_tickets_platform_status",
        table_name="tb_crawl_login_tickets",
    )
    op.drop_index("ix_crawl_login_tickets_account_id", table_name="tb_crawl_login_tickets")
    op.drop_index(
        "ix_crawl_login_tickets_status_expires",
        table_name="tb_crawl_login_tickets",
    )
    op.drop_index("uq_crawl_login_tickets_token", table_name="tb_crawl_login_tickets")
    op.drop_column("tb_crawl_login_tickets", "platform")
    op.rename_table("tb_crawl_login_tickets", "tb_doubao_login_tickets")
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

    op.drop_index(
        "ix_crawl_accounts_platform_status_last_ok",
        table_name="tb_crawl_accounts",
    )
    op.drop_index("uq_crawl_accounts_platform_label", table_name="tb_crawl_accounts")
    op.drop_column("tb_crawl_accounts", "platform")
    op.rename_table("tb_crawl_accounts", "tb_doubao_accounts")
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
