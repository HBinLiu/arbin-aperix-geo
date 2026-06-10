"""Drop deprecated citation URL mention columns."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "010_drop_citation_mentions"
down_revision: Union[str, None] = "009_citation_url_crawl_analysis"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE tb_citation_urls DROP COLUMN IF EXISTS mention_target")
    op.execute("ALTER TABLE tb_citation_urls DROP COLUMN IF EXISTS mention_brand")
    op.execute("ALTER TABLE tb_citation_urls DROP COLUMN IF EXISTS mentions_own")


def downgrade() -> None:
    op.add_column(
        "tb_citation_urls",
        sa.Column("mentions_own", sa.Boolean(), nullable=True),
    )
    op.add_column(
        "tb_citation_urls",
        sa.Column("mention_brand", sa.Boolean(), nullable=True),
    )
    op.add_column(
        "tb_citation_urls",
        sa.Column("mention_target", sa.String(length=255), nullable=False, server_default=""),
    )
