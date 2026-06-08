"""Merge competitor domains/brands into tb_competitors."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "005_competitors_merge"
down_revision: Union[str, None] = "004_prompt_language"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.rename_table("tb_competitor_domains", "tb_competitors")
    op.alter_column("tb_competitors", "site_name", new_column_name="brand")
    op.add_column(
        "tb_competitors",
        sa.Column("summary", sa.Text(), nullable=False, server_default=""),
    )
    op.alter_column("tb_competitors", "summary", server_default=None)

    op.drop_constraint("uq_competitor_domain", "tb_competitors", type_="unique")
    op.drop_index("ix_competitor_domains_subject_id", table_name="tb_competitors")
    op.create_index("ix_competitors_subject_id", "tb_competitors", ["subject_id"])

    conn = op.get_bind()
    conn.execute(
        sa.text(
            """
            INSERT INTO tb_competitors (id, subject_id, domain, website_url, brand, summary, created_at, updated_at)
            SELECT id, subject_id, '', '', name, '', created_at, updated_at
            FROM tb_competitor_brands
            """
        )
    )

    op.drop_index("ix_competitor_brands_subject_id", table_name="tb_competitor_brands")
    op.drop_table("tb_competitor_brands")

    op.create_index(
        "uq_competitors_subject_domain",
        "tb_competitors",
        ["subject_id", "domain"],
        unique=True,
        postgresql_where=sa.text("domain <> ''"),
    )
    op.create_index(
        "uq_competitors_subject_brand_no_domain",
        "tb_competitors",
        ["subject_id", "brand"],
        unique=True,
        postgresql_where=sa.text("domain = ''"),
    )


def downgrade() -> None:
    op.create_table(
        "tb_competitor_brands",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("subject_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["subject_id"], ["tb_subjects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("subject_id", "name", name="uq_competitor_brand"),
    )
    op.create_index("ix_competitor_brands_subject_id", "tb_competitor_brands", ["subject_id"])

    conn = op.get_bind()
    conn.execute(
        sa.text(
            """
            INSERT INTO tb_competitor_brands (id, subject_id, name, created_at, updated_at)
            SELECT id, subject_id, brand, created_at, updated_at
            FROM tb_competitors
            WHERE domain = ''
            """
        )
    )
    conn.execute(sa.text("DELETE FROM tb_competitors WHERE domain = ''"))

    op.drop_index("uq_competitors_subject_brand_no_domain", table_name="tb_competitors")
    op.drop_index("uq_competitors_subject_domain", table_name="tb_competitors")
    op.drop_index("ix_competitors_subject_id", table_name="tb_competitors")

    op.alter_column("tb_competitors", "brand", new_column_name="site_name")
    op.drop_column("tb_competitors", "summary")
    op.rename_table("tb_competitors", "tb_competitor_domains")
    op.create_unique_constraint("uq_competitor_domain", "tb_competitor_domains", ["subject_id", "domain"])
    op.create_index("ix_competitor_domains_subject_id", "tb_competitor_domains", ["subject_id"])
