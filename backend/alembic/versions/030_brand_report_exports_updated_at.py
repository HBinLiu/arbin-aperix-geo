"""Add updated_at column to tb_brand_report_exports."""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "030_report_export_updated_at"
down_revision: Union[str, None] = "029_brand_report_exports_deleted"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("tb_brand_report_exports"):
        return
    columns = {col["name"] for col in inspector.get_columns("tb_brand_report_exports")}
    if "updated_at" not in columns:
        op.add_column(
            "tb_brand_report_exports",
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("tb_brand_report_exports"):
        return
    columns = {col["name"] for col in inspector.get_columns("tb_brand_report_exports")}
    if "updated_at" in columns:
        op.drop_column("tb_brand_report_exports", "updated_at")
