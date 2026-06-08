"""Add page_title to citation URL rows."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "008_citation_url_page_title"
down_revision: Union[str, None] = "007_llm_response_citations"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "tb_citation_urls",
        sa.Column("page_title", sa.String(length=500), nullable=False, server_default=""),
    )
    op.add_column(
        "tb_citation_urls",
        sa.Column("mentions_own", sa.Boolean(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("tb_citation_urls", "mentions_own")
    op.drop_column("tb_citation_urls", "page_title")
