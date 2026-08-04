"""Domain type classification / homepage site_name Celery tasks."""

from __future__ import annotations

from aperix_geo.celery_app import celery_app
from aperix_geo.db.session import SessionLocal
from aperix_geo.services.domain.classify import classify_domains
from aperix_geo.services.domain.site_name import fill_domain_site_names_from_homepage


@celery_app.task(name="aperix_geo.tasks.domain.classify_domain_types", ignore_result=True)
def classify_domain_types(domains: list[str]) -> dict[str, int]:
    """Classify citation domains (seed → homepage rules → LLM); also fills site_name when fetched."""
    db = SessionLocal()
    try:
        result = classify_domains(db, domains)
        db.commit()
        filled = sum(1 for value in result.values() if value.strip())
        return {"domains": len(domains), "filled": filled}
    finally:
        db.close()


@celery_app.task(name="aperix_geo.tasks.domain.resolve_domain_site_names", ignore_result=True)
def resolve_domain_site_names(domains: list[str]) -> dict[str, int]:
    """Fetch registrable-domain homepage and fill DomainProfile.site_name (type already resolved)."""
    db = SessionLocal()
    try:
        found = fill_domain_site_names_from_homepage(db, domains)
        db.commit()
        return {"domains": len(domains), "filled": len(found)}
    finally:
        db.close()
