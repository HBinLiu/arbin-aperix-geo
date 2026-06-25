"""Add soft-delete column to tb_brand_report_exports."""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "029_brand_report_exports_deleted"
down_revision: Union[str, None] = "028_brand_report_exports"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("tb_brand_report_exports"):
        return
    columns = {col["name"] for col in inspector.get_columns("tb_brand_report_exports")}
    if "deleted" not in columns:
        op.add_column(
            "tb_brand_report_exports",
            sa.Column("deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("tb_brand_report_exports"):
        return
    columns = {col["name"] for col in inspector.get_columns("tb_brand_report_exports")}
    if "deleted" in columns:
        op.drop_column("tb_brand_report_exports", "deleted")
