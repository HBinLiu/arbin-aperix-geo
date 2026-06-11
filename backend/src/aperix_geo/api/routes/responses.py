"""Single LLM response evidence."""

from uuid import UUID

from fastapi import APIRouter, HTTPException

from aperix_geo.api.deps import CurrentUser, DbSession
from aperix_geo.db.models import LLMResponse, SamplingJob
from aperix_geo.services.sampling.signals import parsed_api_dict
from aperix_geo.services.subject.loader import load_subject_with_competitors

router = APIRouter(tags=["responses"])


@router.get("/responses/{response_id}")
def get_response(
    response_id: UUID,
    db: DbSession,
    current: CurrentUser,
) -> dict:
    row = db.get(LLMResponse, response_id)
    if not row:
        raise HTTPException(status_code=404, detail="Response not found")
    job = db.get(SamplingJob, row.sampling_job_id)
    if not job or job.tenant_id != current.tenant_id:
        raise HTTPException(status_code=404, detail="Response not found")
    subject = load_subject_with_competitors(db, job.subject_id)
    if not subject:
        raise HTTPException(status_code=404, detail="Response not found")
    raw = row.raw_text or ""
    return {
        "id": str(row.id),
        "sampling_job_id": str(row.sampling_job_id),
        "prompt_id": str(row.prompt_id),
        "platform": row.platform,
        "status": row.status.value,
        "error_text": row.error_text,
        "raw_text": raw,
        "parsed": parsed_api_dict(db, row=row, subject=subject),
        "latency_ms": row.latency_ms,
        "usage": row.usage,
        "created_at": row.created_at.isoformat(),
    }
