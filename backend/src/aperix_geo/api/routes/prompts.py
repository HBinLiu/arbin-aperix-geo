"""Prompts under a subject."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from aperix_geo.api.deps import CurrentUser, DbSession, get_subject_for_user
from aperix_geo.db.models import Prompt
from aperix_geo.schemas.catalog import (
    GenerateSubjectPromptsRequest,
    GeneratedPromptOut,
    PromptBatchCreate,
    PromptCreate,
    PromptOut,
    PromptUpdate,
)
from aperix_geo.services.billing.exceptions import QuotaExceededError
from aperix_geo.services.billing.http import quota_exceeded_http_exception
from aperix_geo.services.prompts.generate import (
    generate_subject_prompt_candidates_for_topic,
    map_generate_error,
)
from aperix_geo.services.prompts.persist import (
    PromptValidationError,
    batch_create_subject_prompts,
    create_subject_prompt,
    get_topic_for_subject,
)
from aperix_geo.services.prompts.taxonomy import normalize_funnel_stage, normalize_search_intent
from aperix_geo.utils.text import prompt_text_hash

router = APIRouter(tags=["prompts"])


def _validation_error(exc: PromptValidationError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


def _prompt_mutation_error(exc: Exception) -> HTTPException:
    if isinstance(exc, QuotaExceededError):
        return quota_exceeded_http_exception(exc)
    if isinstance(exc, PromptValidationError):
        return _validation_error(exc)
    raise exc


@router.get("/subjects/{subject_id}/prompts", response_model=list[PromptOut])
def list_prompts(
    subject_id: UUID,
    db: DbSession,
    current: CurrentUser,
) -> list[Prompt]:
    get_subject_for_user(db, current, subject_id)
    return list(db.execute(select(Prompt).where(Prompt.subject_id == subject_id)).scalars().all())


@router.post("/subjects/{subject_id}/prompts", response_model=PromptOut, status_code=status.HTTP_201_CREATED)
def create_prompt(
    subject_id: UUID,
    body: PromptCreate,
    db: DbSession,
    current: CurrentUser,
) -> Prompt:
    get_subject_for_user(db, current, subject_id)
    try:
        return create_subject_prompt(
            db,
            subject_id,
            topic_id=body.topic_id,
            text=body.text,
            funnel_stage=body.funnel_stage,
            search_intent=body.search_intent,
            enabled=body.enabled,
        )
    except (PromptValidationError, QuotaExceededError) as exc:
        raise _prompt_mutation_error(exc) from exc


@router.post(
    "/subjects/{subject_id}/prompts/batch",
    response_model=list[PromptOut],
    status_code=status.HTTP_201_CREATED,
)
def batch_create_prompts(
    subject_id: UUID,
    body: PromptBatchCreate,
    db: DbSession,
    current: CurrentUser,
) -> list[Prompt]:
    get_subject_for_user(db, current, subject_id)
    try:
        return batch_create_subject_prompts(
            db,
            subject_id,
            topic_id=body.topic_id,
            items=body.items,
        )
    except (PromptValidationError, QuotaExceededError) as exc:
        raise _prompt_mutation_error(exc) from exc


@router.patch("/subjects/{subject_id}/prompts/{prompt_id}", response_model=PromptOut)
def update_prompt(
    subject_id: UUID,
    prompt_id: UUID,
    body: PromptUpdate,
    db: DbSession,
    current: CurrentUser,
) -> Prompt:
    get_subject_for_user(db, current, subject_id)
    p = db.get(Prompt, prompt_id)
    if not p or p.subject_id != subject_id:
        raise HTTPException(status_code=404, detail="提示词不存在")
    if body.topic_id is not None:
        try:
            get_topic_for_subject(db, subject_id, body.topic_id)
        except PromptValidationError as exc:
            raise HTTPException(status_code=400, detail="主题无效") from exc
        p.topic_id = body.topic_id
    if body.text is not None:
        p.text = body.text.strip()
        p.text_hash = prompt_text_hash(p.text)
    if body.funnel_stage is not None:
        p.funnel_stage = normalize_funnel_stage(body.funnel_stage)
    if body.search_intent is not None:
        p.search_intent = normalize_search_intent(body.search_intent)
    if body.enabled is not None:
        p.enabled = body.enabled
    db.commit()
    db.refresh(p)
    return p


def _generate_candidates(
    db: DbSession,
    *,
    subject_id: UUID,
    body: GenerateSubjectPromptsRequest,
    with_competitors: bool,
    current: CurrentUser,
) -> list[dict[str, str]]:
    subject = get_subject_for_user(db, current, subject_id, with_competitors=with_competitors)
    try:
        return generate_subject_prompt_candidates_for_topic(
            db,
            subject=subject,
            subject_id=subject_id,
            topic_id=body.topic_id,
            count=body.count,
        )
    except Exception as exc:
        code, detail = map_generate_error(exc)
        raise HTTPException(status_code=code, detail=detail) from exc


@router.post(
    "/subjects/{subject_id}/prompts/generate/preview",
    response_model=list[GeneratedPromptOut],
)
def preview_subject_prompts(
    subject_id: UUID,
    body: GenerateSubjectPromptsRequest,
    db: DbSession,
    current: CurrentUser,
) -> list[GeneratedPromptOut]:
    rows = _generate_candidates(
        db,
        subject_id=subject_id,
        body=body,
        with_competitors=True,
        current=current,
    )
    return [GeneratedPromptOut(**row) for row in rows]


@router.delete("/subjects/{subject_id}/prompts/{prompt_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_prompt(
    subject_id: UUID,
    prompt_id: UUID,
    db: DbSession,
    current: CurrentUser,
) -> None:
    get_subject_for_user(db, current, subject_id)
    p = db.get(Prompt, prompt_id)
    if not p or p.subject_id != subject_id:
        raise HTTPException(status_code=404, detail="提示词不存在")
    db.delete(p)
    db.commit()
