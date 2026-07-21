"""Domain type classification Celery tasks."""

from __future__ import annotations

from aperix_geo.celery_app import celery_app
from aperix_geo.db.session import SessionLocal
from aperix_geo.services.domain.classify import classify_domains


@celery_app.task(name="aperix_geo.tasks.domain.classify_domain_types", ignore_result=True)
def classify_domain_types(domains: list[str]) -> dict[str, int]:
    """Classify citation domains into Shallalist content types."""
    db = SessionLocal()
    try:
        result = classify_domains(db, domains)
        db.commit()
        filled = sum(1 for value in result.values() if value.strip())
        return {"domains": len(domains), "filled": filled}
    finally:
        db.close()
