"""Citation URL + domain count tables for LLM responses."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "007_llm_response_citations"
down_revision: Union[str, None] = "006_drop_prompt_region_language"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TS = sa.DateTime(timezone=True)
_NOW = sa.text("now()")


def upgrade() -> None:
    op.create_table(
        "tb_citation_domains",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "response_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("tb_llm_responses.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "prompt_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("tb_prompts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("domain", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("cite_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("domain_type", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("created_at", _TS, nullable=False, server_default=_NOW),
        sa.Column("updated_at", _TS, nullable=False, server_default=_NOW),
        sa.UniqueConstraint("response_id", "domain", name="uq_citation_domain"),
    )
    op.create_index("ix_citation_domains_prompt_id", "tb_citation_domains", ["prompt_id"])
    op.create_index("ix_citation_domains_domain", "tb_citation_domains", ["domain"])
    op.create_index("ix_citation_domains_response_id", "tb_citation_domains", ["response_id"])

    op.create_table(
        "tb_citation_urls",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "response_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("tb_llm_responses.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "prompt_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("tb_prompts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("url", sa.Text(), nullable=False, server_default=""),
        sa.Column("mention_brand", sa.Boolean(), nullable=True),
        sa.Column("mention_target", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("fetch_ok", sa.Boolean(), nullable=True),
        sa.Column("from_api", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("url_type", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("created_at", _TS, nullable=False, server_default=_NOW),
        sa.Column("updated_at", _TS, nullable=False, server_default=_NOW),
        sa.UniqueConstraint("response_id", "url", name="uq_citation_url"),
    )
    op.create_index("ix_citation_urls_prompt_id", "tb_citation_urls", ["prompt_id"])
    op.create_index("ix_citation_urls_response_id", "tb_citation_urls", ["response_id"])


def downgrade() -> None:
    op.drop_index("ix_citation_urls_response_id", table_name="tb_citation_urls")
    op.drop_index("ix_citation_urls_prompt_id", table_name="tb_citation_urls")
    op.drop_table("tb_citation_urls")
    op.drop_index("ix_citation_domains_response_id", table_name="tb_citation_domains")
    op.drop_index("ix_citation_domains_domain", table_name="tb_citation_domains")
    op.drop_index("ix_citation_domains_prompt_id", table_name="tb_citation_domains")
    op.drop_table("tb_citation_domains")
