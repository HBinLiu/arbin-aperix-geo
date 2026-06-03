"""Rename primary_domain to website_url; normalize domain; add competitor website_url."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "002_website_url"
down_revision: Union[str, None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _migrate_subject_row(domain: str, primary_domain: str) -> tuple[str, str]:
    from aperix_geo.utils.domains import registrable_domain
    from aperix_geo.utils.url import fallback_website_url, root_website_url

    old_domain = (domain or "").strip()
    old_primary = (primary_domain or "").strip()

    for candidate in (old_primary, old_domain):
        if candidate.lower().startswith(("http://", "https://")):
            url = root_website_url(candidate)
            if url:
                host_domain = registrable_domain(url)
                return host_domain, url

    new_domain = registrable_domain(old_domain or old_primary)
    if not new_domain:
        return "", ""
    return new_domain, fallback_website_url(new_domain)


def upgrade() -> None:
    op.add_column(
        "tb_subjects",
        sa.Column("website_url", sa.String(255), nullable=False, server_default=""),
    )

    conn = op.get_bind()
    rows = conn.execute(sa.text("SELECT id, domain, primary_domain FROM tb_subjects")).fetchall()
    for row in rows:
        new_domain, website_url = _migrate_subject_row(row.domain, row.primary_domain)
        conn.execute(
            sa.text("UPDATE tb_subjects SET domain = :domain, website_url = :website_url WHERE id = :id"),
            {"id": row.id, "domain": new_domain, "website_url": website_url},
        )

    op.drop_column("tb_subjects", "primary_domain")

    op.add_column(
        "tb_competitor_domains",
        sa.Column("website_url", sa.String(255), nullable=False, server_default=""),
    )

    comp_rows = conn.execute(sa.text("SELECT id, domain FROM tb_competitor_domains")).fetchall()
    for row in comp_rows:
        from aperix_geo.utils.domains import registrable_domain
        from aperix_geo.utils.url import fallback_website_url

        new_domain = registrable_domain(row.domain or "")
        website_url = fallback_website_url(new_domain) if new_domain else ""
        conn.execute(
            sa.text(
                "UPDATE tb_competitor_domains SET domain = :domain, website_url = :website_url WHERE id = :id"
            ),
            {"id": row.id, "domain": new_domain, "website_url": website_url},
        )


def downgrade() -> None:
    op.add_column(
        "tb_subjects",
        sa.Column("primary_domain", sa.String(255), nullable=False, server_default=""),
    )

    conn = op.get_bind()
    rows = conn.execute(sa.text("SELECT id, domain, website_url FROM tb_subjects")).fetchall()
    for row in rows:
        conn.execute(
            sa.text("UPDATE tb_subjects SET primary_domain = :primary_domain WHERE id = :id"),
            {"id": row.id, "primary_domain": row.domain or ""},
        )

    op.drop_column("tb_subjects", "website_url")

    op.drop_column("tb_competitor_domains", "website_url")
