"""Rename domain/brand partial unique indexes for clarity."""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "032_rename_domain_brand_uq"
down_revision: Union[str, None] = "031_brand_entity_id"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_RENAMES = (
    ("uq_brands_subject_domain", "uq_brands_domain_nonempty"),
    ("uq_brands_subject_brand_no_domain", "uq_brands_domain_empty_by_brand"),
    ("uq_competitors_subject_domain", "uq_competitors_domain_nonempty"),
    ("uq_competitors_subject_brand_no_domain", "uq_competitors_domain_empty_by_brand"),
)


def upgrade() -> None:
    for old, new in _RENAMES:
        op.execute(f'ALTER INDEX IF EXISTS "{old}" RENAME TO "{new}"')


def downgrade() -> None:
    for old, new in _RENAMES:
        op.execute(f'ALTER INDEX IF EXISTS "{new}" RENAME TO "{old}"')
