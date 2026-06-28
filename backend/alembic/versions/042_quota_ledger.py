"""Evolve usage events into unified tenant quota ledger."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "042_quota_ledger"
down_revision: Union[str, None] = "041_ultimate_platforms"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_ZERO_UUID = sa.text("'00000000-0000-0000-0000-000000000000'::uuid")
_EPOCH = sa.text("'1970-01-01T00:00:00+00:00'::timestamptz")


def upgrade() -> None:
    op.add_column(
        "tb_tenant_usage_events",
        sa.Column("record_type", sa.String(32), nullable=False, server_default="consumption"),
    )
    op.add_column(
        "tb_tenant_usage_events",
        sa.Column("amount_delta", sa.Integer(), nullable=False, server_default="-1"),
    )
    op.execute(
        sa.text(
            """
            UPDATE tb_tenant_usage_events
            SET record_type = 'consumption', amount_delta = -1
            """
        )
    )
    op.alter_column("tb_tenant_usage_events", "record_type", server_default=None)
    op.alter_column("tb_tenant_usage_events", "amount_delta", server_default=None)

    op.execute(
        sa.text(
            """
            INSERT INTO tb_tenant_usage_events (
                id, tenant_id, subject_id, source, reference_id, consumed_from,
                record_type, amount_delta, platform, input_tokens, output_tokens, total_tokens,
                created_at, updated_at, deleted
            )
            SELECT
                gen_random_uuid(),
                o.tenant_id,
                '00000000-0000-0000-0000-000000000000'::uuid,
                'usage_pack',
                o.id,
                '',
                'usage_pack_purchase',
                o.quantity,
                '', 0, 0, 0,
                o.paid_at,
                o.paid_at,
                false
            FROM tb_tenant_pay_orders o
            WHERE o.order_type = 'usage_pack'
              AND o.status = 'paid'
              AND o.paid_at > '1970-01-01T00:00:00+00:00'::timestamptz
              AND o.quantity > 0
              AND NOT EXISTS (
                SELECT 1
                FROM tb_tenant_usage_events l
                WHERE l.tenant_id = o.tenant_id
                  AND l.record_type = 'usage_pack_purchase'
                  AND l.reference_id = o.id
                  AND l.deleted = false
              )
            """
        )
    )

    op.execute(
        sa.text(
            """
            INSERT INTO tb_tenant_usage_events (
                id, tenant_id, subject_id, source, reference_id, consumed_from,
                record_type, amount_delta, platform, input_tokens, output_tokens, total_tokens,
                created_at, updated_at, deleted
            )
            SELECT
                gen_random_uuid(),
                p.tenant_id,
                '00000000-0000-0000-0000-000000000000'::uuid,
                'subscription',
                p.id,
                '',
                'subscription_grant',
                p.monthly_limit,
                '', 0, 0, 0,
                p.period_start,
                p.created_at,
                false
            FROM tb_tenant_usage_periods p
            WHERE p.deleted = false
              AND p.monthly_limit > 0
              AND NOT EXISTS (
                SELECT 1
                FROM tb_tenant_usage_events l
                WHERE l.tenant_id = p.tenant_id
                  AND l.record_type = 'subscription_grant'
                  AND l.reference_id = p.id
                  AND l.deleted = false
              )
            """
        )
    )

    op.drop_index("uq_tenant_usage_events_dedup", table_name="tb_tenant_usage_events")
    op.rename_table("tb_tenant_usage_events", "tb_tenant_quota_ledger")
    op.execute(
        sa.text(
            "ALTER INDEX ix_tenant_usage_events_tenant_created "
            "RENAME TO ix_tenant_quota_ledger_tenant_created"
        )
    )
    op.create_index(
        "uq_tenant_quota_ledger_dedup",
        "tb_tenant_quota_ledger",
        ["tenant_id", "record_type", "reference_id", "source"],
        unique=True,
        postgresql_where=sa.text(
            "reference_id <> '00000000-0000-0000-0000-000000000000'::uuid AND deleted = false"
        ),
    )


def downgrade() -> None:
    op.drop_index("uq_tenant_quota_ledger_dedup", table_name="tb_tenant_quota_ledger")
    op.execute(
        sa.text(
            "ALTER INDEX ix_tenant_quota_ledger_tenant_created "
            "RENAME TO ix_tenant_usage_events_tenant_created"
        )
    )
    op.rename_table("tb_tenant_quota_ledger", "tb_tenant_usage_events")
    op.create_index(
        "uq_tenant_usage_events_dedup",
        "tb_tenant_usage_events",
        ["tenant_id", "reference_id", "source"],
        unique=True,
        postgresql_where=sa.text(
            "reference_id <> '00000000-0000-0000-0000-000000000000'::uuid AND deleted = false"
        ),
    )
    op.execute(
        sa.text(
            """
            DELETE FROM tb_tenant_usage_events
            WHERE record_type IN ('usage_pack_purchase', 'subscription_grant')
            """
        )
    )
    op.drop_column("tb_tenant_usage_events", "amount_delta")
    op.drop_column("tb_tenant_usage_events", "record_type")
