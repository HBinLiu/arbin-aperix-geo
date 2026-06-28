"""Usage event dedup index for idempotent AI billing."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "035_usage_event_dedup"
down_revision: Union[str, None] = "034_subscription_billing"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_ZERO_UUID = sa.text("'00000000-0000-0000-0000-000000000000'::uuid")


def upgrade() -> None:
    op.create_index(
        "uq_tenant_usage_events_dedup",
        "tb_tenant_usage_events",
        ["tenant_id", "reference_id", "source"],
        unique=True,
        postgresql_where=sa.text("reference_id <> '00000000-0000-0000-0000-000000000000'::uuid AND deleted = false"),
    )


def downgrade() -> None:
    op.drop_index("uq_tenant_usage_events_dedup", table_name="tb_tenant_usage_events")
