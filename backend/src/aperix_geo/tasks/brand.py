"""Brand domain backfill Celery tasks."""

from __future__ import annotations

from uuid import UUID

from aperix_geo.celery_app import celery_app
from aperix_geo.db.session import SessionLocal
from aperix_geo.services.brand.backfill import backfill_brand_domains_for_response


@celery_app.task
def backfill_response_brand_domains(response_id: str) -> dict[str, int]:
    """Resolve open-set brand domains via SearXNG after sampling persist."""
    rid = UUID(response_id)
    db = SessionLocal()
    try:
        updated = backfill_brand_domains_for_response(db, rid)
        if updated:
            db.commit()
        return {"updated": updated}
    finally:
        db.close()
