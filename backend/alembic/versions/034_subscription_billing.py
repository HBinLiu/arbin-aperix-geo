"""Subscription billing schema: plans, subscriptions, usage periods, pay orders."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "034_subscription_billing"
down_revision: Union[str, None] = "033_user_wechat_notifications"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TS = sa.DateTime(timezone=True)
_NOW = sa.text("now()")
_EPOCH = sa.text("'1970-01-01T00:00:00+00:00'::timestamptz")
_ZERO_UUID = sa.text("'00000000-0000-0000-0000-000000000000'::uuid")

_STD_COLS = (
    sa.Column("created_at", _TS, nullable=False, server_default=_NOW),
    sa.Column("updated_at", _TS, nullable=False, server_default=_NOW),
    sa.Column("deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
)


def _create_plans() -> None:
    op.create_table(
        "tb_plans",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("code", sa.String(32), nullable=False),
        sa.Column("name", sa.String(64), nullable=False),
        sa.Column("max_subjects", sa.Integer(), nullable=False),
        sa.Column("max_per_platforms", sa.Integer(), nullable=False),
        sa.Column("max_per_competitors", sa.Integer(), nullable=False),
        sa.Column("max_prompts_total", sa.Integer(), nullable=False),
        sa.Column("per_month_usages", sa.Integer(), nullable=False),
        sa.Column("sampling_frequency", sa.String(32), nullable=False, server_default="daily_1"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("sort_order", sa.SmallInteger(), nullable=False, server_default="0"),
        *_STD_COLS,
    )
    op.create_index("uq_plans_code", "tb_plans", ["code"], unique=True, postgresql_where=sa.text("deleted = false"))


def _create_plan_prices() -> None:
    op.create_table(
        "tb_plan_prices",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("plan_id", sa.Uuid(as_uuid=True), sa.ForeignKey("tb_plans.id", ondelete="CASCADE"), nullable=False),
        sa.Column("billing_cycle", sa.String(16), nullable=False),
        sa.Column("monthly_cents", sa.Integer(), nullable=False),
        sa.Column("period_total_cents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("discount_label", sa.String(16), nullable=False, server_default=""),
        *_STD_COLS,
    )
    op.create_index(
        "uq_plan_prices_plan_cycle",
        "tb_plan_prices",
        ["plan_id", "billing_cycle"],
        unique=True,
        postgresql_where=sa.text("deleted = false"),
    )


def _create_plan_usage_products() -> None:
    op.create_table(
        "tb_plan_usage_products",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("code", sa.String(32), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("price_cents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("unit_price_cents", sa.Integer(), nullable=False),
        sa.Column("min_quantity", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("sort_order", sa.SmallInteger(), nullable=False, server_default="0"),
        *_STD_COLS,
    )
    op.create_index(
        "uq_plan_usage_products_code",
        "tb_plan_usage_products",
        ["code"],
        unique=True,
        postgresql_where=sa.text("deleted = false"),
    )


def _create_tenant_subscriptions() -> None:
    op.create_table(
        "tb_tenant_subscriptions",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(as_uuid=True), sa.ForeignKey("tb_tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("plan_id", sa.Uuid(as_uuid=True), sa.ForeignKey("tb_plans.id"), nullable=False),
        sa.Column("billing_cycle", sa.String(16), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("current_period_start", _TS, nullable=False),
        sa.Column("current_period_end", _TS, nullable=False),
        sa.Column("pending_plan_id", sa.Uuid(as_uuid=True), nullable=False, server_default=_ZERO_UUID),
        sa.Column("canceled_at", _TS, nullable=False, server_default=_EPOCH),
        sa.Column("pay_channel", sa.String(128), nullable=False, server_default=""),
        *_STD_COLS,
    )
    op.create_index("ix_tenant_subscriptions_tenant_id", "tb_tenant_subscriptions", ["tenant_id"])
    op.create_index(
        "uq_tenant_subscriptions_tenant",
        "tb_tenant_subscriptions",
        ["tenant_id"],
        unique=True,
        postgresql_where=sa.text("deleted = false"),
    )


def _create_tenant_usage_periods() -> None:
    op.create_table(
        "tb_tenant_usage_periods",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(as_uuid=True), sa.ForeignKey("tb_tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "subscription_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("tb_tenant_subscriptions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("period_start", _TS, nullable=False),
        sa.Column("period_end", _TS, nullable=False),
        sa.Column("monthly_limit", sa.Integer(), nullable=False),
        sa.Column("monthly_used", sa.Integer(), nullable=False, server_default="0"),
        *_STD_COLS,
    )
    op.create_index(
        "uq_tenant_usage_periods_tenant_start",
        "tb_tenant_usage_periods",
        ["tenant_id", "period_start"],
        unique=True,
        postgresql_where=sa.text("deleted = false"),
    )
    op.create_index("ix_tenant_usage_periods_period_end", "tb_tenant_usage_periods", ["period_end"])


def _create_tenant_plan_overrides() -> None:
    op.create_table(
        "tb_tenant_plan_overrides",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(as_uuid=True), sa.ForeignKey("tb_tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("max_subjects", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_per_platforms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_per_competitors", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_prompts_total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("per_month_usages", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("sampling_frequency", sa.String(32), nullable=False, server_default=""),
        sa.Column("note", sa.Text(), nullable=False, server_default=""),
        *_STD_COLS,
    )
    op.create_index(
        "uq_tenant_plan_overrides_tenant",
        "tb_tenant_plan_overrides",
        ["tenant_id"],
        unique=True,
        postgresql_where=sa.text("deleted = false"),
    )


def _create_tenant_pay_orders() -> None:
    op.create_table(
        "tb_tenant_pay_orders",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(as_uuid=True), sa.ForeignKey("tb_tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=False, server_default=_ZERO_UUID),
        sa.Column("order_type", sa.String(32), nullable=False),
        sa.Column("amount_cents", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("paid_at", _TS, nullable=False, server_default=_EPOCH),
        sa.Column("payment_id", sa.String(128), nullable=False, server_default=""),
        sa.Column("plan_id", sa.Uuid(as_uuid=True), nullable=False, server_default=_ZERO_UUID),
        sa.Column("billing_cycle", sa.String(16), nullable=False, server_default=""),
        sa.Column("period_start", _TS, nullable=False, server_default=_EPOCH),
        sa.Column("period_end", _TS, nullable=False, server_default=_EPOCH),
        sa.Column("product_code", sa.String(32), nullable=False, server_default=""),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("unit_price_cents", sa.Integer(), nullable=False, server_default="0"),
        *_STD_COLS,
    )
    op.create_index(
        "ix_tenant_pay_orders_tenant_created",
        "tb_tenant_pay_orders",
        ["tenant_id", sa.text("created_at DESC")],
    )
    op.create_index("ix_tenant_pay_orders_status", "tb_tenant_pay_orders", ["status"])


def _create_tenant_usage_events() -> None:
    op.create_table(
        "tb_tenant_usage_events",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(as_uuid=True), sa.ForeignKey("tb_tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("subject_id", sa.Uuid(as_uuid=True), nullable=False, server_default=_ZERO_UUID),
        sa.Column("source", sa.String(32), nullable=False),
        sa.Column("reference_id", sa.Uuid(as_uuid=True), nullable=False, server_default=_ZERO_UUID),
        sa.Column("consumed_from", sa.String(16), nullable=False),
        *_STD_COLS,
    )
    op.create_index(
        "ix_tenant_usage_events_tenant_created",
        "tb_tenant_usage_events",
        ["tenant_id", sa.text("created_at DESC")],
    )


def _seed_catalog() -> None:
    op.execute(
        sa.text(
            """
            INSERT INTO tb_plans (
                id, code, name, max_subjects, max_per_platforms, max_per_competitors,
                max_prompts_total, per_month_usages, sampling_frequency, is_active, sort_order
            ) VALUES
                ('11111111-1111-4111-8111-111111111101', 'personal', '个人版', 1, 3, 10, 50, 2500, 'daily_1', true, 1),
                ('11111111-1111-4111-8111-111111111102', 'premium', '专业版', 3, 3, 10, 150, 8500, 'daily_1', true, 2),
                ('11111111-1111-4111-8111-111111111103', 'ultimate', '旗舰版', 5, 3, 10, 300, 15000, 'daily_1', true, 3),
                ('11111111-1111-4111-8111-111111111104', 'enterprise', '企业版', 999999, 999999, 999999, 999999, 999999, 'daily_1', true, 4)
            """
        )
    )
    op.execute(
        sa.text(
            """
            INSERT INTO tb_plan_prices (id, plan_id, billing_cycle, monthly_cents, period_total_cents, discount_label)
            VALUES
                (gen_random_uuid(), '11111111-1111-4111-8111-111111111101', 'monthly', 29900, 29900, ''),
                (gen_random_uuid(), '11111111-1111-4111-8111-111111111101', 'quarterly', 26900, 80700, '-10%'),
                (gen_random_uuid(), '11111111-1111-4111-8111-111111111101', 'yearly', 23900, 286800, '-20%'),
                (gen_random_uuid(), '11111111-1111-4111-8111-111111111102', 'monthly', 89900, 89900, ''),
                (gen_random_uuid(), '11111111-1111-4111-8111-111111111102', 'quarterly', 80900, 242700, '-10%'),
                (gen_random_uuid(), '11111111-1111-4111-8111-111111111102', 'yearly', 71900, 862800, '-20%'),
                (gen_random_uuid(), '11111111-1111-4111-8111-111111111103', 'monthly', 149900, 149900, ''),
                (gen_random_uuid(), '11111111-1111-4111-8111-111111111103', 'quarterly', 134900, 404700, '-10%'),
                (gen_random_uuid(), '11111111-1111-4111-8111-111111111103', 'yearly', 119900, 1438800, '-20%'),
                (gen_random_uuid(), '11111111-1111-4111-8111-111111111104', 'monthly', 0, 0, ''),
                (gen_random_uuid(), '11111111-1111-4111-8111-111111111104', 'quarterly', 0, 0, ''),
                (gen_random_uuid(), '11111111-1111-4111-8111-111111111104', 'yearly', 0, 0, '')
            """
        )
    )
    op.execute(
        sa.text(
            """
            INSERT INTO tb_plan_usage_products (id, code, quantity, price_cents, unit_price_cents, min_quantity, sort_order)
            VALUES
                (gen_random_uuid(), 'pack_1000', 1000, 12900, 13, 100, 1),
                (gen_random_uuid(), 'pack_5000', 5000, 59900, 12, 100, 2),
                (gen_random_uuid(), 'pack_10000', 10000, 99900, 10, 100, 3),
                (gen_random_uuid(), 'custom', 0, 0, 15, 100, 4)
            """
        )
    )


def _backfill_tenant_subscriptions() -> None:
    op.execute(
        sa.text(
            """
            INSERT INTO tb_tenant_subscriptions (
                id, tenant_id, plan_id, billing_cycle, status,
                current_period_start, current_period_end
            )
            SELECT
                gen_random_uuid(),
                t.id,
                '11111111-1111-4111-8111-111111111101',
                'monthly',
                'active',
                now(),
                now() + interval '1 month'
            FROM tb_tenants t
            WHERE t.deleted = false
              AND NOT EXISTS (
                  SELECT 1 FROM tb_tenant_subscriptions s
                  WHERE s.tenant_id = t.id AND s.deleted = false
              )
            """
        )
    )
    op.execute(
        sa.text(
            """
            INSERT INTO tb_tenant_usage_periods (
                id, tenant_id, subscription_id, period_start, period_end, monthly_limit
            )
            SELECT
                gen_random_uuid(),
                s.tenant_id,
                s.id,
                s.current_period_start,
                s.current_period_start + interval '1 month',
                p.per_month_usages
            FROM tb_tenant_subscriptions s
            JOIN tb_plans p ON p.id = s.plan_id
            WHERE s.deleted = false
              AND NOT EXISTS (
                  SELECT 1 FROM tb_tenant_usage_periods up
                  WHERE up.tenant_id = s.tenant_id AND up.deleted = false
              )
            """
        )
    )


def upgrade() -> None:
    _create_plans()
    _create_plan_prices()
    _create_plan_usage_products()
    _create_tenant_subscriptions()
    _create_tenant_usage_periods()
    _create_tenant_plan_overrides()
    _create_tenant_pay_orders()
    _create_tenant_usage_events()

    op.add_column(
        "tb_tenants",
        sa.Column("usage_pack_balance", sa.Integer(), nullable=False, server_default="0"),
    )
    op.execute(
        sa.text(
            "ALTER TABLE tb_tenants ADD CONSTRAINT ck_tb_tenants_usage_pack_balance_nonneg "
            "CHECK (usage_pack_balance >= 0)"
        )
    )

    op.add_column(
        "tb_subjects",
        sa.Column("sampling_frequency", sa.String(32), nullable=False, server_default="daily_1"),
    )

    _seed_catalog()
    _backfill_tenant_subscriptions()


def downgrade() -> None:
    op.drop_column("tb_subjects", "sampling_frequency")
    op.execute(sa.text("ALTER TABLE tb_tenants DROP CONSTRAINT IF EXISTS ck_tb_tenants_usage_pack_balance_nonneg"))
    op.drop_column("tb_tenants", "usage_pack_balance")

    op.drop_index("ix_tenant_usage_events_tenant_created", table_name="tb_tenant_usage_events")
    op.drop_table("tb_tenant_usage_events")

    op.drop_index("ix_tenant_pay_orders_status", table_name="tb_tenant_pay_orders")
    op.drop_index("ix_tenant_pay_orders_tenant_created", table_name="tb_tenant_pay_orders")
    op.drop_table("tb_tenant_pay_orders")

    op.drop_index("uq_tenant_plan_overrides_tenant", table_name="tb_tenant_plan_overrides")
    op.drop_table("tb_tenant_plan_overrides")

    op.drop_index("ix_tenant_usage_periods_period_end", table_name="tb_tenant_usage_periods")
    op.drop_index("uq_tenant_usage_periods_tenant_start", table_name="tb_tenant_usage_periods")
    op.drop_table("tb_tenant_usage_periods")

    op.drop_index("uq_tenant_subscriptions_tenant", table_name="tb_tenant_subscriptions")
    op.drop_index("ix_tenant_subscriptions_tenant_id", table_name="tb_tenant_subscriptions")
    op.drop_table("tb_tenant_subscriptions")

    op.drop_index("uq_plan_usage_products_code", table_name="tb_plan_usage_products")
    op.drop_table("tb_plan_usage_products")

    op.drop_index("uq_plan_prices_plan_cycle", table_name="tb_plan_prices")
    op.drop_table("tb_plan_prices")

    op.drop_index("uq_plans_code", table_name="tb_plans")
    op.drop_table("tb_plans")
