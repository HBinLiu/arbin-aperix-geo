"""Create and persist prompts under a subject."""

from __future__ import annotations

from typing import Mapping, Protocol
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from aperix_geo.db.models import Prompt, Subject, Topic, ZERO_UUID
from aperix_geo.services.billing.exceptions import QuotaExceededError
from aperix_geo.services.billing.quota import assert_can_add_prompts, remaining_prompt_slots
from aperix_geo.services.prompts.taxonomy import normalize_funnel_stage, normalize_search_intent
from aperix_geo.services.prompts.taxonomy import normalize_decision_type
from aperix_geo.utils.text import prompt_text_hash

PROMPT_KIND_ROOT = "root"
PROMPT_KIND_FANOUT = "fanout"


class PromptValidationError(ValueError):
    """Invalid prompt input or quota exceeded."""


class _PromptInput(Protocol):
    text: str
    funnel_stage: str
    search_intent: str
    decision_type: str


def _decision_type_from_mapping(item: Mapping[str, str]) -> str:
    return str(item.get("decision_type") or "")


def _read_prompt_item(item: _PromptInput | Mapping[str, str]) -> tuple[str, str, str, str]:
    if isinstance(item, Mapping):
        return (
            str(item.get("text") or ""),
            str(item.get("funnel_stage") or "mofu"),
            str(item.get("search_intent") or "commercial"),
            _decision_type_from_mapping(item),
        )
    return item.text, item.funnel_stage, item.search_intent, item.decision_type


def get_topic_for_subject(db: Session, subject_id: UUID, topic_id: UUID) -> Topic:
    topic = db.get(Topic, topic_id)
    if not topic or topic.subject_id != subject_id:
        raise PromptValidationError("该主体下不存在此主题")
    return topic


def _tenant_id_for_subject(db: Session, subject_id: UUID) -> UUID:
    tenant_id = db.scalar(
        select(Subject.tenant_id).where(Subject.id == subject_id, Subject.deleted.is_(False)).limit(1)
    )
    if tenant_id is None:
        raise PromptValidationError("主体不存在")
    return tenant_id


def remaining_prompt_slots_for_subject(db: Session, subject_id: UUID) -> int:
    tenant_id = _tenant_id_for_subject(db, subject_id)
    return remaining_prompt_slots(db, tenant_id)


def _assert_can_add(db: Session, subject_id: UUID, *, count: int) -> None:
    tenant_id = _tenant_id_for_subject(db, subject_id)
    try:
        assert_can_add_prompts(db, tenant_id, count=count)
    except QuotaExceededError as exc:
        raise PromptValidationError(str(exc)) from exc


def _text_hash_exists(db: Session, subject_id: UUID, text_hash: str) -> bool:
    return (
        db.execute(
            select(Prompt.id)
            .where(Prompt.subject_id == subject_id, Prompt.text_hash == text_hash, Prompt.deleted.is_(False))
            .limit(1),
        ).scalar_one_or_none()
        is not None
    )


def _build_prompt(
    *,
    subject_id: UUID,
    topic_id: UUID,
    text: str,
    funnel_stage: str,
    search_intent: str,
    decision_type: str = "",
    enabled: bool,
    parent_prompt_id: UUID = ZERO_UUID,
    kind: str = PROMPT_KIND_ROOT,
    origin_query: str = "",
) -> Prompt:
    normalized = text.strip()
    return Prompt(
        subject_id=subject_id,
        topic_id=topic_id,
        text=normalized,
        text_hash=prompt_text_hash(normalized),
        funnel_stage=normalize_funnel_stage(funnel_stage),
        search_intent=normalize_search_intent(search_intent),
        decision_type=normalize_decision_type(decision_type),
        enabled=enabled,
        parent_prompt_id=parent_prompt_id,
        kind=kind,
        origin_query=origin_query.strip(),
    )


def create_subject_prompt(
    db: Session,
    subject_id: UUID,
    *,
    topic_id: UUID,
    text: str,
    funnel_stage: str = "mofu",
    search_intent: str = "commercial",
    decision_type: str = "",
    enabled: bool = True,
) -> Prompt:
    get_topic_for_subject(db, subject_id, topic_id)
    _assert_can_add(db, subject_id, count=1)

    normalized = text.strip()
    if not normalized:
        raise PromptValidationError("提示词内容不能为空")

    text_hash = prompt_text_hash(normalized)
    if _text_hash_exists(db, subject_id, text_hash):
        raise PromptValidationError("该主体下已存在相同提示词")

    prompt = _build_prompt(
        subject_id=subject_id,
        topic_id=topic_id,
        text=normalized,
        funnel_stage=funnel_stage,
        search_intent=search_intent,
        decision_type=decision_type,
        enabled=enabled,
    )
    db.add(prompt)
    db.commit()
    db.refresh(prompt)
    return prompt


_BATCH_EMPTY_OR_DUP = "提示词均为空或已存在，未能添加"


def batch_create_subject_prompts(
    db: Session,
    subject_id: UUID,
    *,
    topic_id: UUID,
    items: list[_PromptInput | Mapping[str, str]],
) -> list[Prompt]:
    get_topic_for_subject(db, subject_id, topic_id)
    _assert_can_add(db, subject_id, count=len(items))

    pending_hashes: set[str] = set()
    created: list[Prompt] = []
    for item in items:
        text, funnel_stage, search_intent, decision_type = _read_prompt_item(item)
        normalized = text.strip()
        if not normalized:
            continue

        text_hash = prompt_text_hash(normalized)
        if text_hash in pending_hashes or _text_hash_exists(db, subject_id, text_hash):
            continue

        pending_hashes.add(text_hash)
        prompt = _build_prompt(
            subject_id=subject_id,
            topic_id=topic_id,
            text=normalized,
            funnel_stage=funnel_stage,
            search_intent=search_intent,
            decision_type=decision_type,
            enabled=True,
        )
        db.add(prompt)
        created.append(prompt)

    if not created:
        raise PromptValidationError(_BATCH_EMPTY_OR_DUP)

    db.commit()
    for prompt in created:
        db.refresh(prompt)
    return created


def promote_fanout_prompt(
    db: Session,
    subject_id: UUID,
    *,
    parent_prompt_id: UUID,
    query: str,
    enabled: bool = False,
) -> Prompt:
    """Create a kind=fanout child prompt from an observed search query."""
    parent = db.get(Prompt, parent_prompt_id)
    if parent is None or parent.subject_id != subject_id or parent.deleted:
        raise PromptValidationError("父提示词不存在")
    if str(parent.kind or PROMPT_KIND_ROOT) == PROMPT_KIND_FANOUT:
        raise PromptValidationError("不能从扇出提示词再次晋升")

    normalized = query.strip()
    if not normalized:
        raise PromptValidationError("查询词不能为空")

    _assert_can_add(db, subject_id, count=1)
    text_hash = prompt_text_hash(normalized)
    if _text_hash_exists(db, subject_id, text_hash):
        raise PromptValidationError("该主体下已存在相同提示词")

    prompt = _build_prompt(
        subject_id=subject_id,
        topic_id=parent.topic_id,
        text=normalized,
        funnel_stage=parent.funnel_stage,
        search_intent=parent.search_intent,
        decision_type=parent.decision_type,
        enabled=enabled,
        parent_prompt_id=parent.id,
        kind=PROMPT_KIND_FANOUT,
        origin_query=normalized,
    )
    db.add(prompt)
    db.flush()
    from aperix_geo.services.sampling.prompt_fanouts import mark_prompt_fanout_promoted

    mark_prompt_fanout_promoted(
        db,
        subject_id=subject_id,
        parent_prompt_id=parent.id,
        query=normalized,
        promoted_prompt_id=prompt.id,
    )
    db.commit()
    db.refresh(prompt)
    return prompt
