"""Add language to prompts."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "004_prompt_language"
down_revision: Union[str, None] = "003_prompt_regions"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "tb_prompts",
        sa.Column("language", sa.String(length=16), nullable=False, server_default=""),
    )


def downgrade() -> None:
    op.drop_column("tb_prompts", "language")
