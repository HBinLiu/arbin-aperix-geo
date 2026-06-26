"""Add tb_brands.entity_id; drop brand cross_validate columns."""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "031_brand_entity_id"
down_revision: Union[str, None] = "030_report_export_updated_at"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "tb_brands",
        sa.Column("entity_id", sa.String(64), nullable=False, server_default=""),
    )

    op.execute(sa.text("UPDATE tb_brands SET entity_id = 'own' WHERE entity_kind = 'own'"))

    op.execute(
        sa.text(
            """
            UPDATE tb_brands b
            SET entity_id = c.id::text
            FROM tb_competitors c
            WHERE b.subject_id = c.subject_id
              AND b.entity_kind = 'competitor'
              AND b.entity_id = ''
              AND (
                (b.domain <> '' AND b.domain = c.domain)
                OR (b.domain = '' AND lower(b.brand) = lower(c.brand))
              )
            """
        )
    )

    op.create_index(
        "uq_brands_subject_entity_id",
        "tb_brands",
        ["subject_id", "entity_id"],
        unique=True,
        postgresql_where=sa.text("entity_id <> '' AND deleted = false"),
    )

    op.drop_column("tb_brands", "cross_validated_at")
    op.drop_column("tb_brands", "cross_validate_reason")
    op.drop_column("tb_brands", "cross_validate_score")


def downgrade() -> None:
    op.add_column("tb_brands", sa.Column("cross_validate_score", sa.Float(), nullable=True))
    op.add_column(
        "tb_brands",
        sa.Column("cross_validate_reason", sa.Text(), nullable=False, server_default=""),
    )
    op.add_column("tb_brands", sa.Column("cross_validated_at", sa.DateTime(timezone=True), nullable=True))

    op.drop_index("uq_brands_subject_entity_id", table_name="tb_brands")
    op.drop_column("tb_brands", "entity_id")
