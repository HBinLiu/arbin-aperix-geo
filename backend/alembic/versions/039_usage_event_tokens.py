"""Add platform and token counts to tenant usage events."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "039_usage_event_tokens"
down_revision: Union[str, None] = "038_subj_topics_prompts"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "tb_tenant_usage_events",
        sa.Column("platform", sa.String(128), nullable=False, server_default=""),
    )
    op.add_column(
        "tb_tenant_usage_events",
        sa.Column("input_tokens", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "tb_tenant_usage_events",
        sa.Column("output_tokens", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "tb_tenant_usage_events",
        sa.Column("total_tokens", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("tb_tenant_usage_events", "total_tokens")
    op.drop_column("tb_tenant_usage_events", "output_tokens")
    op.drop_column("tb_tenant_usage_events", "input_tokens")
    op.drop_column("tb_tenant_usage_events", "platform")
