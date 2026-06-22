"""Generate monitoring prompts for an existing subject topic (LLM only, no persist)."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from aperix_geo.db.models import Prompt, Subject, Topic
from aperix_geo.services.prompts import PROMPT_QUOTA_LIMIT, generate_setup_prompts
from aperix_geo.services.prompts.context import prompt_context_from_subject
from aperix_geo.services.prompts.persist import (
    PromptValidationError,
    get_topic_for_subject,
    remaining_prompt_slots,
)
from aperix_geo.services.providers import LLMProviderError


def generate_subject_prompt_candidates(
    db: Session,
    *,
    subject: Subject,
    topic: Topic,
    count: int,
) -> list[dict[str, str]]:
    """Call LLM and return up to ``count`` prompt rows for the topic (not persisted)."""
    remaining = remaining_prompt_slots(db, subject.id)
    if remaining <= 0:
        raise PromptValidationError(f"提示词已达上限（{PROMPT_QUOTA_LIMIT} 条）")

    take = min(count, remaining)
    ctx = prompt_context_from_subject(subject)
    existing_prompts = list(
        db.execute(select(Prompt.text).where(Prompt.subject_id == subject.id)).scalars().all()
    )

    items = generate_setup_prompts(
        entity=str(ctx["entity"]),
        topics=[topic.name],
        industry=str(ctx["industry"]),
        features=str(ctx["features"]),
        customers=str(ctx["customers"]),
        competitors=[str(c) for c in ctx["competitors"] if str(c).strip()],
        aliases=[str(a) for a in ctx["aliases"] if str(a).strip()],
        prompts_per_topic=take,
        exclude_prompts=existing_prompts,
    )

    generated = items[0]["prompts"] if items else []
    rows: list[dict[str, str]] = []
    for row in generated[:take]:
        text = str(row.get("text") or "").strip()
        if not text:
            continue
        rows.append(
            {
                "text": text,
                "funnel_stage": str(row.get("funnel_stage") or "mofu"),
                "search_intent": str(row.get("search_intent") or "commercial"),
            }
        )
    if not rows:
        raise ValueError("未能生成任何提示词")
    return rows


def generate_subject_prompt_candidates_for_topic(
    db: Session,
    *,
    subject: Subject,
    subject_id: UUID,
    topic_id: UUID,
    count: int,
) -> list[dict[str, str]]:
    topic = get_topic_for_subject(db, subject_id, topic_id)
    return generate_subject_prompt_candidates(db, subject=subject, topic=topic, count=count)


def map_generate_error(exc: Exception) -> tuple[int, str]:
    if isinstance(exc, LLMProviderError):
        return 502, f"提示词生成失败：{exc}"
    if isinstance(exc, PromptValidationError):
        return 400, str(exc)
    if isinstance(exc, ValueError):
        return 400, str(exc)
    raise exc
