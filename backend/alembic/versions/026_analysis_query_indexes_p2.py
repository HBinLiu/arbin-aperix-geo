"""Add P2 indexes for prompt/topic filters and domain prompt breakdown."""

from typing import Sequence, Union

from alembic import op

revision: str = "026_analysis_query_indexes_p2"
down_revision: Union[str, None] = "025_analysis_query_indexes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "ix_llm_responses_prompt_status_created",
        "tb_llm_responses",
        ["prompt_id", "status", "created_at"],
    )
    op.create_index(
        "ix_citation_domains_domain_prompt",
        "tb_citation_domains",
        ["domain", "prompt_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_citation_domains_domain_prompt", table_name="tb_citation_domains")
    op.drop_index("ix_llm_responses_prompt_status_created", table_name="tb_llm_responses")
