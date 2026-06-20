"""Use 0 as unset sentiment_score sentinel (replace -1)."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "016_sentiment_score_zero_default"
down_revision: Union[str, None] = "015_signal_schema_refactor"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TABLE = "tb_llm_response_signals"


def upgrade() -> None:
    op.execute(
        sa.text(
            f"UPDATE {_TABLE} "
            "SET sentiment_score = 0 "
            "WHERE sentiment_score < 0"
        )
    )
    op.alter_column(
        _TABLE,
        "sentiment_score",
        existing_type=sa.Float(),
        server_default="0",
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            f"UPDATE {_TABLE} "
            "SET sentiment_score = -1 "
            "WHERE sentiment_score = 0 AND sentiment_reason = ''"
        )
    )
    op.alter_column(
        _TABLE,
        "sentiment_score",
        existing_type=sa.Float(),
        server_default="-1",
    )
