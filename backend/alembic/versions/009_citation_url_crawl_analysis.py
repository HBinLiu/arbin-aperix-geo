"""Add citation URL crawl metadata and LLM analysis fields."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "009_citation_url_crawl_analysis"
down_revision: Union[str, None] = "008_citation_url_page_title"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "tb_citation_urls",
        "url_type",
        existing_type=sa.String(length=64),
        type_=sa.String(length=128),
        existing_nullable=False,
        existing_server_default="",
    )
    op.add_column("tb_citation_urls", sa.Column("domain_type", sa.String(length=128), nullable=False, server_default=""))
    op.add_column("tb_citation_urls", sa.Column("http_status", sa.Integer(), nullable=True))
    op.add_column("tb_citation_urls", sa.Column("description", sa.Text(), nullable=False, server_default=""))
    op.add_column("tb_citation_urls", sa.Column("headings", sa.Text(), nullable=False, server_default=""))
    op.add_column("tb_citation_urls", sa.Column("has_table", sa.Boolean(), nullable=True))
    op.add_column("tb_citation_urls", sa.Column("has_code_block", sa.Boolean(), nullable=True))
    op.add_column("tb_citation_urls", sa.Column("text_snippet", sa.Text(), nullable=False, server_default=""))
    op.add_column(
        "tb_citation_urls",
        sa.Column("llm_analysis", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
    )
    op.alter_column(
        "tb_citation_domains",
        "domain_type",
        existing_type=sa.String(length=64),
        type_=sa.String(length=128),
        existing_nullable=False,
        existing_server_default="",
    )


def downgrade() -> None:
    op.alter_column(
        "tb_citation_domains",
        "domain_type",
        existing_type=sa.String(length=128),
        type_=sa.String(length=64),
        existing_nullable=False,
        existing_server_default="",
    )
    op.drop_column("tb_citation_urls", "llm_analysis")
    op.drop_column("tb_citation_urls", "text_snippet")
    op.drop_column("tb_citation_urls", "has_code_block")
    op.drop_column("tb_citation_urls", "has_table")
    op.drop_column("tb_citation_urls", "headings")
    op.drop_column("tb_citation_urls", "description")
    op.drop_column("tb_citation_urls", "http_status")
    op.drop_column("tb_citation_urls", "domain_type")
    op.alter_column(
        "tb_citation_urls",
        "url_type",
        existing_type=sa.String(length=128),
        type_=sa.String(length=64),
        existing_nullable=False,
        existing_server_default="",
    )
