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
from aperix_geo.services.providers import LLMProviderError
from aperix_geo.services.subject.loader import competitor_lists
from aperix_geo.utils.text import prompt_text_hash

router = APIRouter(tags=["prompts"])


def _scope_region_language(subject: Subject) -> tuple[str, str]:
    scope = subject.monitoring_scope if isinstance(subject.monitoring_scope, dict) else {}
    region = str(scope.get("region") or "CN").strip() or "CN"
    language = str(scope.get("language") or "zh-CN").strip() or "zh-CN"
    return region, language


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
    region, language = _scope_region_language(subject)

    entity = (subject.brand or subject.domain or "").strip() or "本品牌"
    domains, brands = competitor_lists(subject)
    competitors = [*domains, *brands]

    try:
        items = generate_setup_prompts(
            entity=entity,
            topics=[topic.name],
            industry="",
            core_features=subject.profile_summary or "",
            target_customers="",
            competitors=competitors,
            region=region,
            language=language,
            prompts_per_topic=count,
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
    for text in generated[:count]:
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
