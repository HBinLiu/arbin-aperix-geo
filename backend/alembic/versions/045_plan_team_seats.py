"""Update AI monthly quotas and add team seat limits to plans."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "045_plan_team_seats"
down_revision: Union[str, None] = "044_user_role"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "tb_plans",
        sa.Column("max_team_members", sa.Integer(), nullable=False, server_default="3"),
    )
    op.add_column(
        "tb_tenant_plan_overrides",
        sa.Column("max_team_members", sa.Integer(), nullable=False, server_default="0"),
    )

    op.execute(
        sa.text(
            """
            UPDATE tb_plans SET per_month_usages = 2000, max_team_members = 3
            WHERE code = 'personal' AND deleted = false
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE tb_plans SET per_month_usages = 7000, max_team_members = 5
            WHERE code = 'premium' AND deleted = false
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE tb_plans SET per_month_usages = 12000, max_team_members = 10
            WHERE code = 'ultimate' AND deleted = false
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE tb_plans SET max_team_members = 999999
            WHERE code = 'enterprise' AND deleted = false
            """
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            """
            UPDATE tb_plans SET per_month_usages = 2500
            WHERE code = 'personal' AND deleted = false
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE tb_plans SET per_month_usages = 8500
            WHERE code = 'premium' AND deleted = false
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE tb_plans SET per_month_usages = 15000
            WHERE code = 'ultimate' AND deleted = false
            """
        )
    )
    op.drop_column("tb_tenant_plan_overrides", "max_team_members")
    op.drop_column("tb_plans", "max_team_members")
