"""Setup wizard Celery tasks."""

from __future__ import annotations

from uuid import UUID

from aperix_geo.celery_app import celery_app
from aperix_geo.services.setup.discover import run_discover_setup_job


@celery_app.task
def setup_discover_profile(
    *,
    user_id: str,
    tenant_id: str,
    session_id: str,
    subject_type: str,
    target: str,
    region: str,
    language: str,
    website_url: str,
    profile_hash: str,
) -> dict[str, str]:
    """Crawl + niche-profile LLM; write Redis session / discover job status."""
    run_discover_setup_job(
        user_id=user_id,
        tenant_id=UUID(tenant_id),
        session_id=session_id,
        subject_type=subject_type,
        target=target,
        region=region,
        language=language,
        website_url=website_url,
        profile_hash=profile_hash,
    )
    return {"session_id": session_id, "status": "done"}
