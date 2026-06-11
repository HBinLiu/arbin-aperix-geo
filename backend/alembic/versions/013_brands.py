"""Add tenant-scoped tb_brands and link tb_llm_response_signals to brands."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "013_brands"
down_revision: Union[str, None] = "012_llm_response_signals"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "tb_brands",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("brand", sa.String(length=255), nullable=False),
        sa.Column("domain", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("website_url", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("aliases", JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("summary", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tb_tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_brands_tenant_id", "tb_brands", ["tenant_id"])
    op.create_index("ix_brands_tenant_brand", "tb_brands", ["tenant_id", "brand"])
    op.create_index(
        "uq_brands_tenant_domain",
        "tb_brands",
        ["tenant_id", "domain"],
        unique=True,
        postgresql_where=sa.text("domain <> ''"),
    )
    op.create_index(
        "uq_brands_tenant_brand_no_domain",
        "tb_brands",
        ["tenant_id", "brand"],
        unique=True,
        postgresql_where=sa.text("domain = ''"),
    )

    op.add_column("tb_llm_response_signals", sa.Column("brand_id", sa.Uuid(), nullable=True))
    op.add_column(
        "tb_llm_response_signals",
        sa.Column("entity_label", sa.String(length=255), nullable=False, server_default=""),
    )
    op.add_column(
        "tb_llm_response_signals",
        sa.Column("primary_domain", sa.String(length=255), nullable=False, server_default=""),
    )
    op.create_foreign_key(
        "fk_llm_response_signals_brand_id",
        "tb_llm_response_signals",
        "tb_brands",
        ["brand_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_llm_response_signals_brand_id", "tb_llm_response_signals", ["brand_id"])


def downgrade() -> None:
    op.drop_index("ix_llm_response_signals_brand_id", table_name="tb_llm_response_signals")
    op.drop_constraint("fk_llm_response_signals_brand_id", "tb_llm_response_signals", type_="foreignkey")
    op.drop_column("tb_llm_response_signals", "primary_domain")
    op.drop_column("tb_llm_response_signals", "entity_label")
    op.drop_column("tb_llm_response_signals", "brand_id")

    op.drop_index("uq_brands_tenant_brand_no_domain", table_name="tb_brands")
    op.drop_index("uq_brands_tenant_domain", table_name="tb_brands")
    op.drop_index("ix_brands_tenant_brand", table_name="tb_brands")
    op.drop_index("ix_brands_tenant_id", table_name="tb_brands")
    op.drop_table("tb_brands")
