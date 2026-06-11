"""Prompts under a subject."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select

from aperix_geo.api.deps import CurrentUser, DbSession, get_subject_for_user
from aperix_geo.db.models import Prompt, Subject, Topic
from aperix_geo.schemas.catalog import (
    GenerateSubjectPromptsRequest,
    PromptCreate,
    PromptOut,
    PromptUpdate,
)
from aperix_geo.services.prompts import PROMPT_MAX_PER_TOPIC, generate_setup_prompts
from aperix_geo.services.prompts.context import prompt_context_from_subject
from aperix_geo.services.providers import LLMProviderError
from aperix_geo.services.prompts.taxonomy import normalize_funnel_stage, normalize_search_intent
from aperix_geo.utils.text import prompt_text_hash

router = APIRouter(tags=["prompts"])


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
    topic = db.get(Topic, body.topic_id)
    if not topic or topic.subject_id != subject_id:
        raise HTTPException(status_code=400, detail="Invalid topic_id for this subject")
    th = prompt_text_hash(body.text)
    dup = db.execute(select(Prompt).where(Prompt.subject_id == subject_id, Prompt.text_hash == th)).scalar_one_or_none()
    if dup:
        raise HTTPException(status_code=400, detail="Duplicate prompt text for this subject")
    p = Prompt(
        subject_id=subject_id,
        topic_id=body.topic_id,
        text=body.text.strip(),
        text_hash=th,
        funnel_stage=normalize_funnel_stage(body.funnel_stage),
        search_intent=normalize_search_intent(body.search_intent),
        enabled=body.enabled,
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


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
        raise HTTPException(status_code=404, detail="Prompt not found")
    if body.topic_id is not None:
        topic = db.get(Topic, body.topic_id)
        if not topic or topic.subject_id != subject_id:
            raise HTTPException(status_code=400, detail="Invalid topic_id")
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


@router.post(
    "/subjects/{subject_id}/prompts/generate",
    response_model=list[PromptOut],
    status_code=status.HTTP_201_CREATED,
)
def generate_subject_prompts(
    subject_id: UUID,
    body: GenerateSubjectPromptsRequest,
    db: DbSession,
    current: CurrentUser,
) -> list[Prompt]:
    subject = get_subject_for_user(db, current, subject_id, with_competitors=True)

    topic = db.get(Topic, body.topic_id)
    if not topic or topic.subject_id != subject_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid topic_id for this subject")

    existing_count = db.execute(
        select(func.count(Prompt.id)).where(Prompt.topic_id == body.topic_id),
    ).scalar_one()
    remaining = PROMPT_MAX_PER_TOPIC - int(existing_count)
    if remaining <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Topic already has {PROMPT_MAX_PER_TOPIC} prompts",
        )

    count = min(body.count, remaining)
    ctx = prompt_context_from_subject(subject)

    existing_prompts = list(
        db.execute(select(Prompt.text).where(Prompt.topic_id == body.topic_id)).scalars().all()
    )

    try:
        items = generate_setup_prompts(
            entity=str(ctx["entity"]),
            topics=[topic.name],
            industry=str(ctx["industry"]),
            core_features=str(ctx["core_features"]),
            target_customers=str(ctx["target_customers"]),
            competitors=[str(c) for c in ctx["competitors"] if str(c).strip()],
            aliases=[str(a) for a in ctx["aliases"] if str(a).strip()],
            prompts_per_topic=count,
            exclude_prompts=existing_prompts,
        )
    except (LLMProviderError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"提示词生成失败：{exc}",
        ) from exc

    generated = items[0]["prompts"] if items else []
    if not generated:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="No prompts generated")

    created: list[Prompt] = []
    for row in generated[:count]:
        text = str(row.get("text") or "").strip()
        if not text:
            continue
        th = prompt_text_hash(text)
        dup = db.execute(
            select(Prompt).where(Prompt.subject_id == subject_id, Prompt.text_hash == th),
        ).scalar_one_or_none()
        if dup:
            continue
        prompt = Prompt(
            subject_id=subject_id,
            topic_id=body.topic_id,
            text=text,
            text_hash=th,
            funnel_stage=normalize_funnel_stage(str(row.get("funnel_stage") or "")),
            search_intent=normalize_search_intent(str(row.get("search_intent") or "")),
            enabled=True,
        )
        db.add(prompt)
        created.append(prompt)

    if not created:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="All generated prompts already exist")

    db.commit()
    for prompt in created:
        db.refresh(prompt)
    return created


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
        raise HTTPException(status_code=404, detail="Prompt not found")
    db.delete(p)
    db.commit()
