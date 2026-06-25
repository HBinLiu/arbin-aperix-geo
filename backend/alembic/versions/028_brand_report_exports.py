"""Brand report export audit log (on-demand PDF, decoupled from sampling jobs)."""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "028_brand_report_exports"
down_revision: Union[str, None] = "027_citation_domain_registrable"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if inspector.has_table("tb_brand_reports"):
        op.drop_index("uq_brand_reports_sampling_job", table_name="tb_brand_reports")
        op.drop_index("ix_brand_reports_subject_created", table_name="tb_brand_reports")
        op.drop_table("tb_brand_reports")
    op.execute("DROP TYPE IF EXISTS brand_report_status")

    op.create_table(
        "tb_brand_report_exports",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("subject_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("window_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("entity_id", sa.String(length=64), nullable=False, server_default=""),
        sa.Column(
            "platform",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "topic_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("format", sa.String(length=16), nullable=False, server_default="pdf"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.ForeignKeyConstraint(["subject_id"], ["tb_subjects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tb_tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["tb_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_brand_report_exports_subject_created",
        "tb_brand_report_exports",
        ["subject_id", "created_at"],
    )
    op.create_index(
        "ix_brand_report_exports_tenant_user_created",
        "tb_brand_report_exports",
        ["tenant_id", "user_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_brand_report_exports_tenant_user_created", table_name="tb_brand_report_exports")
    op.drop_index("ix_brand_report_exports_subject_created", table_name="tb_brand_report_exports")
    op.drop_table("tb_brand_report_exports")
