"""Add crawl_ready to llm_response_status enum."""

from __future__ import annotations

from typing import Union

from alembic import op

revision: str = "024_llm_response_crawl_ready"
down_revision: Union[str, None] = "023_llm_responses_job_status_idx"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE llm_response_status ADD VALUE IF NOT EXISTS 'crawl_ready'")


def downgrade() -> None:
    pass
