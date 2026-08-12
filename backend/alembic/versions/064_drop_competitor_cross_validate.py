"""Drop unused cross_validate_* columns from tb_competitors."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "064_drop_comp_cross_validate"
down_revision: Union[str, None] = "063_domain_profile_site_name"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TS = sa.DateTime(timezone=True)
_EPOCH = sa.text("'1970-01-01T00:00:00+00:00'::timestamptz")


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col["name"] for col in inspector.get_columns("tb_competitors")}
    for name in ("cross_validated_at", "cross_validate_reason", "cross_validate_score"):
        if name in columns:
            op.drop_column("tb_competitors", name)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col["name"] for col in inspector.get_columns("tb_competitors")}
    if "cross_validate_score" not in columns:
        op.add_column(
            "tb_competitors",
            sa.Column("cross_validate_score", sa.Float(), nullable=False, server_default="0"),
        )
    if "cross_validate_reason" not in columns:
        op.add_column(
            "tb_competitors",
            sa.Column("cross_validate_reason", sa.Text(), nullable=False, server_default=""),
        )
    if "cross_validated_at" not in columns:
        op.add_column(
            "tb_competitors",
            sa.Column("cross_validated_at", _TS, nullable=False, server_default=_EPOCH),
        )
