"""Rename pack_purchase ledger record type to usage_pack_purchase."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "043_usage_pack_purchase_type"
down_revision: Union[str, None] = "042_quota_ledger"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            UPDATE tb_tenant_quota_ledger
            SET record_type = 'usage_pack_purchase'
            WHERE record_type = 'pack_purchase'
            """
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            """
            UPDATE tb_tenant_quota_ledger
            SET record_type = 'pack_purchase'
            WHERE record_type = 'usage_pack_purchase'
            """
        )
    )
