"""Add indexes for analysis citation/backlink and signal window queries."""

from typing import Sequence, Union

from alembic import op

revision: str = "025_analysis_query_indexes"
down_revision: Union[str, None] = "024_llm_response_crawl_ready"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "ix_llm_response_signals_subject_kind_created",
        "tb_llm_response_signals",
        ["subject_id", "entity_kind", "created_at"],
    )
    op.create_index(
        "ix_llm_response_signals_subject_kind_cited",
        "tb_llm_response_signals",
        ["subject_id", "entity_kind", "cited_on_source"],
    )
    op.create_index(
        "ix_citation_domains_domain_response",
        "tb_citation_domains",
        ["domain", "response_id"],
    )
    op.create_index(
        "ix_citation_urls_url_response",
        "tb_citation_urls",
        ["url", "response_id"],
    )
    op.create_index(
        "ix_llm_responses_job_status_created",
        "tb_llm_responses",
        ["sampling_job_id", "status", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_llm_responses_job_status_created", table_name="tb_llm_responses")
    op.drop_index("ix_citation_urls_url_response", table_name="tb_citation_urls")
    op.drop_index("ix_citation_domains_domain_response", table_name="tb_citation_domains")
    op.drop_index("ix_llm_response_signals_subject_kind_cited", table_name="tb_llm_response_signals")
    op.drop_index("ix_llm_response_signals_subject_kind_created", table_name="tb_llm_response_signals")
