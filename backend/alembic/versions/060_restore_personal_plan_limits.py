"""Restore personal plan brand/prompt limits to seed values."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "060_restore_personal_plan_limits"
down_revision: Union[str, None] = "059_drop_user_password"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Align with 034 seed: personal max_subjects=1, max_prompts_total=50
    op.execute(
        sa.text(
            """
            UPDATE tb_plans
            SET max_subjects = 1,
                max_prompts_total = 50,
                updated_at = now()
            WHERE code = 'personal' AND deleted = false
            """
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            """
            UPDATE tb_plans
            SET max_subjects = 3,
                max_prompts_total = 150,
                updated_at = now()
            WHERE code = 'personal' AND deleted = false
            """
        )
    )
