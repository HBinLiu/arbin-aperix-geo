"""Add url_type to citation URLs (English page-type codes)."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "052_citation_url_type"
down_revision: Union[str, None] = "051_domain_profiles"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "tb_citation_urls",
        sa.Column("url_type", sa.String(length=64), nullable=False, server_default=""),
    )
    op.create_index("ix_citation_urls_url_type", "tb_citation_urls", ["url_type"])


def downgrade() -> None:
    op.drop_index("ix_citation_urls_url_type", table_name="tb_citation_urls")
    op.drop_column("tb_citation_urls", "url_type")
