"""Add composite index on llm_responses (sampling_job_id, status)."""

from typing import Sequence, Union

from alembic import op

revision: str = "023_llm_responses_job_status_idx"
down_revision: Union[str, None] = "022_llm_response_llm_ready"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "ix_llm_responses_job_status",
        "tb_llm_responses",
        ["sampling_job_id", "status"],
    )


def downgrade() -> None:
    op.drop_index("ix_llm_responses_job_status", table_name="tb_llm_responses")
