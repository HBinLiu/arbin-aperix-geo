"""Add AI quota reservation columns for sampling jobs."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "061_sampling_quota_reserve"
down_revision: Union[str, None] = "060_restore_personal_plan_limits"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "tb_tenant_usage_periods",
        sa.Column("monthly_reserved", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "tb_tenants",
        sa.Column("usage_pack_reserved", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "tb_sampling_jobs",
        sa.Column("quota_reserved_monthly", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "tb_sampling_jobs",
        sa.Column("quota_reserved_pack", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "tb_sampling_jobs",
        sa.Column("quota_open_monthly", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "tb_sampling_jobs",
        sa.Column("quota_open_pack", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "tb_llm_responses",
        sa.Column("quota_settled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )


def downgrade() -> None:
    op.drop_column("tb_llm_responses", "quota_settled")
    op.drop_column("tb_sampling_jobs", "quota_open_pack")
    op.drop_column("tb_sampling_jobs", "quota_open_monthly")
    op.drop_column("tb_sampling_jobs", "quota_reserved_pack")
    op.drop_column("tb_sampling_jobs", "quota_reserved_monthly")
    op.drop_column("tb_tenants", "usage_pack_reserved")
    op.drop_column("tb_tenant_usage_periods", "monthly_reserved")
