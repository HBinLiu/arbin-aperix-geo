"""Subject-scoped brands, niche_profile, cross-validate scores."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "020_brand_competitive_scope"
down_revision: Union[str, None] = "schema_table_soft_delete"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TS = sa.DateTime(timezone=True)


def upgrade() -> None:
    op.add_column(
        "tb_subjects",
        sa.Column(
            "niche_profile",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )

    op.add_column("tb_competitors", sa.Column("cross_validate_score", sa.Float(), nullable=True))
    op.add_column("tb_competitors", sa.Column("cross_validate_reason", sa.Text(), nullable=False, server_default=""))
    op.add_column("tb_competitors", sa.Column("cross_validated_at", _TS, nullable=True))

    op.add_column("tb_brands", sa.Column("subject_id", sa.Uuid(as_uuid=True), nullable=True))
    op.add_column(
        "tb_brands",
        sa.Column("entity_kind", sa.String(16), nullable=False, server_default="other"),
    )
    op.add_column("tb_brands", sa.Column("cross_validate_score", sa.Float(), nullable=True))
    op.add_column("tb_brands", sa.Column("cross_validate_reason", sa.Text(), nullable=False, server_default=""))
    op.add_column("tb_brands", sa.Column("cross_validated_at", _TS, nullable=True))
    op.add_column("tb_brands", sa.Column("source", sa.String(32), nullable=False, server_default=""))

    op.execute(
        sa.text(
            """
            UPDATE tb_brands b
            SET subject_id = agg.subject_id
            FROM (
                SELECT DISTINCT ON (brand_id) brand_id, subject_id
                FROM tb_llm_response_signals
                ORDER BY brand_id, subject_id
            ) agg
            WHERE b.id = agg.brand_id AND b.subject_id IS NULL
            """
        )
    )
    op.execute(sa.text("DELETE FROM tb_brands WHERE subject_id IS NULL"))

    op.drop_index("uq_brands_tenant_brand_no_domain", table_name="tb_brands")
    op.drop_index("uq_brands_tenant_domain", table_name="tb_brands")
    op.drop_index("ix_brands_tenant_brand", table_name="tb_brands")
    op.drop_index("ix_brands_tenant_id", table_name="tb_brands")
    op.drop_constraint("tb_brands_tenant_id_fkey", "tb_brands", type_="foreignkey")
    op.drop_column("tb_brands", "tenant_id")

    op.alter_column("tb_brands", "subject_id", nullable=False)
    op.create_foreign_key(
        "tb_brands_subject_id_fkey",
        "tb_brands",
        "tb_subjects",
        ["subject_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_brands_subject_id", "tb_brands", ["subject_id"])
    op.create_index("ix_brands_subject_brand", "tb_brands", ["subject_id", "brand"])
    op.create_index(
        "uq_brands_subject_domain",
        "tb_brands",
        ["subject_id", "domain"],
        unique=True,
        postgresql_where=sa.text("domain <> '' AND deleted = false"),
    )
    op.create_index(
        "uq_brands_subject_brand_no_domain",
        "tb_brands",
        ["subject_id", "brand"],
        unique=True,
        postgresql_where=sa.text("domain = '' AND deleted = false"),
    )


def downgrade() -> None:
    op.drop_index("uq_brands_subject_brand_no_domain", table_name="tb_brands")
    op.drop_index("uq_brands_subject_domain", table_name="tb_brands")
    op.drop_index("ix_brands_subject_brand", table_name="tb_brands")
    op.drop_index("ix_brands_subject_id", table_name="tb_brands")
    op.drop_constraint("tb_brands_subject_id_fkey", "tb_brands", type_="foreignkey")

    op.add_column("tb_brands", sa.Column("tenant_id", sa.Uuid(as_uuid=True), nullable=True))
    op.execute(
        sa.text(
            """
            UPDATE tb_brands b
            SET tenant_id = s.tenant_id
            FROM tb_subjects s
            WHERE b.subject_id = s.id
            """
        )
    )
    op.alter_column("tb_brands", "tenant_id", nullable=False)
    op.create_foreign_key(
        "tb_brands_tenant_id_fkey",
        "tb_brands",
        "tb_tenants",
        ["tenant_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_brands_tenant_id", "tb_brands", ["tenant_id"])
    op.create_index("ix_brands_tenant_brand", "tb_brands", ["tenant_id", "brand"])
    op.create_index(
        "uq_brands_tenant_domain",
        "tb_brands",
        ["tenant_id", "domain"],
        unique=True,
        postgresql_where=sa.text("domain <> '' AND deleted = false"),
    )
    op.create_index(
        "uq_brands_tenant_brand_no_domain",
        "tb_brands",
        ["tenant_id", "brand"],
        unique=True,
        postgresql_where=sa.text("domain = '' AND deleted = false"),
    )

    op.drop_column("tb_brands", "source")
    op.drop_column("tb_brands", "cross_validated_at")
    op.drop_column("tb_brands", "cross_validate_reason")
    op.drop_column("tb_brands", "cross_validate_score")
    op.drop_column("tb_brands", "entity_kind")
    op.drop_column("tb_brands", "subject_id")

    op.drop_column("tb_competitors", "cross_validated_at")
    op.drop_column("tb_competitors", "cross_validate_reason")
    op.drop_column("tb_competitors", "cross_validate_score")

    op.drop_column("tb_subjects", "niche_profile")
