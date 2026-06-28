"""Rename usage event source prompt_generate -> prompt."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "040_usage_event_prompt_src"
down_revision: Union[str, None] = "039_usage_event_tokens"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            UPDATE tb_tenant_usage_events
            SET source = 'prompt'
            WHERE source = 'prompt_generate' AND deleted = false
            """
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            """
            UPDATE tb_tenant_usage_events
            SET source = 'prompt_generate'
            WHERE source = 'prompt' AND deleted = false
            """
        )
    )
