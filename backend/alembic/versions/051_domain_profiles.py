"""Domain profiles for Shallalist content-type classification."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "051_domain_profiles"
down_revision: Union[str, None] = "050_drop_topic_decision_dim"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TS = sa.DateTime(timezone=True)
_NOW = sa.text("now()")


def upgrade() -> None:
    op.create_table(
        "tb_domain_profiles",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("domain", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("domain_type", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("source", sa.String(length=32), nullable=False, server_default=""),
        sa.Column("created_at", _TS, nullable=False, server_default=_NOW),
        sa.Column("updated_at", _TS, nullable=False, server_default=_NOW),
        sa.Column("deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.create_index(
        "uq_domain_profiles_domain",
        "tb_domain_profiles",
        ["domain"],
        unique=True,
        postgresql_where=sa.text("deleted = false"),
    )
    op.create_index("ix_domain_profiles_domain_type", "tb_domain_profiles", ["domain_type"])


def downgrade() -> None:
    op.drop_index("ix_domain_profiles_domain_type", table_name="tb_domain_profiles")
    op.drop_index("uq_domain_profiles_domain", table_name="tb_domain_profiles")
    op.drop_table("tb_domain_profiles")
