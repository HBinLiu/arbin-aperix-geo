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
    PromptFanoutPromote,
    PromptOut,
    PromptTaxonomyOut,
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
    promote_fanout_prompt,
)
from aperix_geo.services.prompts.taxonomy import (
    normalize_decision_type,
    normalize_funnel_stage,
    normalize_search_intent,
    prompt_taxonomy_meta,
)
from aperix_geo.utils.text import prompt_text_hash

router = APIRouter(tags=["prompts"])


@router.get("/prompts/taxonomy", response_model=PromptTaxonomyOut)
def get_prompt_taxonomy(_current: CurrentUser) -> PromptTaxonomyOut:
    meta = prompt_taxonomy_meta()
    return PromptTaxonomyOut(
        funnel_stages=[{"value": item.value, "label": item.label} for item in meta.funnel_stages],
        search_intents=[{"value": item.value, "label": item.label} for item in meta.search_intents],
        decision_types=[{"value": item.value, "label": item.label} for item in meta.decision_types],
        default_funnel_stage=meta.default_funnel_stage,
        default_search_intent=meta.default_search_intent,
        default_decision_type=meta.default_decision_type,
    )


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
    kind: str | None = None,
) -> list[Prompt]:
    """List prompts. Default returns all kinds; pass ``kind=root`` or ``kind=fanout`` to filter."""
    get_subject_for_user(db, current, subject_id)
    q = select(Prompt).where(Prompt.subject_id == subject_id)
    kind_filter = (kind or "").strip().lower()
    if kind_filter and kind_filter != "all":
        q = q.where(Prompt.kind == kind_filter)
    return list(db.execute(q.order_by(Prompt.created_at.asc())).scalars().all())


@router.post(
    "/subjects/{subject_id}/prompts/{prompt_id}/fanout",
    response_model=PromptOut,
    status_code=status.HTTP_201_CREATED,
)
def promote_prompt_fanout(
    subject_id: UUID,
    prompt_id: UUID,
    body: PromptFanoutPromote,
    db: DbSession,
    current: CurrentUser,
) -> Prompt:
    get_subject_for_user(db, current, subject_id)
    try:
        return promote_fanout_prompt(
            db,
            subject_id,
            parent_prompt_id=prompt_id,
            query=body.query,
            enabled=body.enabled,
        )
    except (PromptValidationError, QuotaExceededError) as exc:
        raise _prompt_mutation_error(exc) from exc


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
            decision_type=body.decision_type,
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
    if body.decision_type is not None:
        p.decision_type = normalize_decision_type(body.decision_type)
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
            funnel_stage=body.funnel_stage,
            search_intent=body.search_intent,
            decision_type=body.decision_type,
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
