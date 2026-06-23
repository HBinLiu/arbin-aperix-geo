"""Normalize tb_citation_domains.domain to registrable (eTLD+1)."""

from __future__ import annotations

from collections import defaultdict
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "027_citation_domain_registrable"
down_revision: Union[str, None] = "026_analysis_query_indexes_p2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    from aperix_geo.utils.domains import normalize_host, registrable_domain

    conn = op.get_bind()
    rows = conn.execute(
        sa.text(
            "SELECT id, response_id, prompt_id, domain, cite_count "
            "FROM tb_citation_domains"
        )
    ).fetchall()
    if not rows:
        return

    merged: dict[tuple, dict] = defaultdict(lambda: {"cite_count": 0, "prompt_id": None, "keep_id": None, "drop_ids": []})
    for row in rows:
        old_domain = str(row.domain or "")
        new_domain = registrable_domain(old_domain) or normalize_host(old_domain)
        if not new_domain:
            conn.execute(sa.text("DELETE FROM tb_citation_domains WHERE id = :id"), {"id": row.id})
            continue
        key = (row.response_id, new_domain)
        bucket = merged[key]
        bucket["cite_count"] += int(row.cite_count or 0)
        bucket["prompt_id"] = row.prompt_id
        if bucket["keep_id"] is None:
            bucket["keep_id"] = row.id
        else:
            bucket["drop_ids"].append(row.id)

    for (_response_id, domain), data in merged.items():
        conn.execute(
            sa.text(
                "UPDATE tb_citation_domains "
                "SET domain = :domain, cite_count = :cite_count "
                "WHERE id = :id"
            ),
            {
                "id": data["keep_id"],
                "domain": domain,
                "cite_count": data["cite_count"],
            },
        )
        for drop_id in data["drop_ids"]:
            conn.execute(sa.text("DELETE FROM tb_citation_domains WHERE id = :id"), {"id": drop_id})


def downgrade() -> None:
    # Data normalization is not reversible.
    pass
