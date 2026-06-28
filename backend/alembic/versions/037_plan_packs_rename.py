"""Rename tb_plan_usage_products to tb_plan_packs."""

from typing import Sequence, Union

from alembic import op

revision: str = "037_plan_packs_rename"
down_revision: Union[str, None] = "036_user_notifications"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.rename_table("tb_plan_usage_products", "tb_plan_packs")
    op.execute("ALTER INDEX uq_plan_usage_products_code RENAME TO uq_plan_packs_code")


def downgrade() -> None:
    op.execute("ALTER INDEX uq_plan_packs_code RENAME TO uq_plan_usage_products_code")
    op.rename_table("tb_plan_packs", "tb_plan_usage_products")
