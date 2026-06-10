"""Favicon pre-warm Celery task."""

from __future__ import annotations

from uuid import UUID

from aperix_geo.celery_app import celery_app
from aperix_geo.db.session import SessionLocal
from aperix_geo.services.favicon._warm import citation_hosts_for_job, warm_favicon_hosts


@celery_app.task
def warm_favicons_for_job(job_id: str) -> dict[str, int]:
    """Background pre-warm favicons for citation hosts after sampling completes."""
    jid = UUID(job_id)
    db = SessionLocal()
    try:
        hosts = citation_hosts_for_job(db, jid)
    finally:
        db.close()
    return warm_favicon_hosts(hosts, job_id=job_id)
