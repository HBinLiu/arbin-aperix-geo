"""Raise ultimate plan max_per_platforms to 6."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "041_ultimate_platforms"
down_revision: Union[str, None] = "040_usage_event_prompt_src"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            UPDATE tb_plans
            SET max_per_platforms = 6, updated_at = now()
            WHERE code = 'ultimate' AND deleted = false
            """
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            """
            UPDATE tb_plans
            SET max_per_platforms = 3, updated_at = now()
            WHERE code = 'ultimate' AND deleted = false
            """
        )
    )
