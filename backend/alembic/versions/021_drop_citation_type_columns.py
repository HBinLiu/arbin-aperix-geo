"""Drop domain_type and url_type from citation tables."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "021_drop_citation_type_columns"
down_revision: Union[str, None] = "020_brand_competitive_scope"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("tb_citation_domains", "domain_type")
    op.drop_column("tb_citation_urls", "domain_type")
    op.drop_column("tb_citation_urls", "url_type")


def downgrade() -> None:
    op.add_column(
        "tb_citation_urls",
        sa.Column("url_type", sa.String(128), nullable=False, server_default=""),
    )
    op.add_column(
        "tb_citation_urls",
        sa.Column("domain_type", sa.String(128), nullable=False, server_default=""),
    )
    op.add_column(
        "tb_citation_domains",
        sa.Column("domain_type", sa.String(128), nullable=False, server_default=""),
    )
