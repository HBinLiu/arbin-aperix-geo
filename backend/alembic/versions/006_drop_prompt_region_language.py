"""Drop regions and language from prompts."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "006_drop_prompt_region_language"
down_revision: Union[str, None] = "005_competitors_merge"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("tb_prompts", "language")
    op.drop_column("tb_prompts", "regions")


def downgrade() -> None:
    op.add_column(
        "tb_prompts",
        sa.Column(
            "regions",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.add_column(
        "tb_prompts",
        sa.Column("language", sa.String(length=16), nullable=False, server_default=""),
    )
    op.alter_column("tb_prompts", "regions", server_default=None)
    op.alter_column("tb_prompts", "language", server_default=None)
