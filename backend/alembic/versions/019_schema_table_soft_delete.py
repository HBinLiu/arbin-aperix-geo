"""Add deleted soft-delete flag to all ORM tables."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "schema_table_soft_delete"
down_revision: Union[str, None] = "018_drop_monitoring_scope"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TABLES = (
    "tb_tenants",
    "tb_users",
    "tb_brands",
    "tb_subjects",
    "tb_competitors",
    "tb_topics",
    "tb_prompts",
    "tb_sampling_jobs",
    "tb_llm_responses",
    "tb_llm_response_signals",
    "tb_citation_domains",
    "tb_citation_urls",
)

_PARTIAL_UNIQUE_INDEXES = (
    ("tb_users", "uq_users_phone", ["phone"], "phone <> '' AND deleted = false"),
    ("tb_users", "uq_users_tenant_email_nn", ["tenant_id", "email"], "email <> '' AND deleted = false"),
    ("tb_brands", "uq_brands_tenant_domain", ["tenant_id", "domain"], "domain <> '' AND deleted = false"),
    (
        "tb_brands",
        "uq_brands_tenant_brand_no_domain",
        ["tenant_id", "brand"],
        "domain = '' AND deleted = false",
    ),
    (
        "tb_competitors",
        "uq_competitors_subject_domain",
        ["subject_id", "domain"],
        "domain <> '' AND deleted = false",
    ),
    (
        "tb_competitors",
        "uq_competitors_subject_brand_no_domain",
        ["subject_id", "brand"],
        "domain = '' AND deleted = false",
    ),
)

_CONSTRAINT_TO_PARTIAL_INDEX = (
    ("tb_prompts", "uq_subject_prompt_hash", ["subject_id", "text_hash"]),
    ("tb_llm_responses", "uq_job_prompt_platform", ["sampling_job_id", "prompt_id", "platform"]),
    ("tb_llm_response_signals", "uq_llm_response_signal", ["response_id", "entity_id"]),
    ("tb_citation_domains", "uq_citation_domain", ["response_id", "domain"]),
    ("tb_citation_urls", "uq_citation_url", ["response_id", "url"]),
)


def _drop_index_if_exists(table: str, name: str) -> None:
    op.execute(sa.text(f'DROP INDEX IF EXISTS "{name}"'))


def _recreate_partial_unique_indexes() -> None:
    for table, name, columns, where in _PARTIAL_UNIQUE_INDEXES:
        _drop_index_if_exists(table, name)
        op.create_index(
            name,
            table,
            columns,
            unique=True,
            postgresql_where=sa.text(where),
        )

    for table, name, columns in _CONSTRAINT_TO_PARTIAL_INDEX:
        op.drop_constraint(name, table, type_="unique")
        op.create_index(
            name,
            table,
            columns,
            unique=True,
            postgresql_where=sa.text("deleted = false"),
        )


def _restore_old_unique_indexes() -> None:
    for table, name, columns in reversed(_CONSTRAINT_TO_PARTIAL_INDEX):
        _drop_index_if_exists(table, name)
        op.create_unique_constraint(name, table, columns)

    old_partials = (
        ("tb_users", "uq_users_phone", ["phone"], "phone <> ''"),
        ("tb_users", "uq_users_tenant_email_nn", ["tenant_id", "email"], "email <> ''"),
        ("tb_brands", "uq_brands_tenant_domain", ["tenant_id", "domain"], "domain <> ''"),
        ("tb_brands", "uq_brands_tenant_brand_no_domain", ["tenant_id", "brand"], "domain = ''"),
        (
            "tb_competitors",
            "uq_competitors_subject_domain",
            ["subject_id", "domain"],
            "domain <> ''",
        ),
        (
            "tb_competitors",
            "uq_competitors_subject_brand_no_domain",
            ["subject_id", "brand"],
            "domain = ''",
        ),
    )
    for table, name, columns, where in old_partials:
        _drop_index_if_exists(table, name)
        op.create_index(
            name,
            table,
            columns,
            unique=True,
            postgresql_where=sa.text(where),
        )


def upgrade() -> None:
    for table in _TABLES:
        op.add_column(
            table,
            sa.Column("deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        )

    _recreate_partial_unique_indexes()


def downgrade() -> None:
    _restore_old_unique_indexes()

    for table in reversed(_TABLES):
        op.drop_column(table, "deleted")
