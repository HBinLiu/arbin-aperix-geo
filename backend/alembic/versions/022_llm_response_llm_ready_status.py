"""Add llm_ready to llm_response_status enum."""

from typing import Sequence, Union

from alembic import op

revision: str = "022_llm_response_llm_ready"
down_revision: Union[str, None] = "021_drop_citation_type_columns"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE llm_response_status ADD VALUE IF NOT EXISTS 'llm_ready'")


def downgrade() -> None:
    # PostgreSQL cannot remove enum values safely; no-op.
    pass
