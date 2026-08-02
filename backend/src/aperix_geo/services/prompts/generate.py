"""Generate monitoring prompts for an existing subject topic (LLM only, no persist)."""

from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from aperix_geo.db.models import Prompt, Subject, Topic
from aperix_geo.services.billing.exceptions import QuotaExceededError, SubscriptionInactiveError
from aperix_geo.services.billing.http import (
    quota_exceeded_http_exception,
    subscription_inactive_http_exception,
)
from aperix_geo.services.billing.quota import assert_ai_usage_available, consume_ai_usage, usage_reference
from aperix_geo.services.billing.usage_tokens import SETUP_LLM_PLATFORM
from aperix_geo.services.competitor.types import NicheProfile
from aperix_geo.services.prompts.context import prompt_context_from_subject
from aperix_geo.services.prompts.persist import (
    PromptValidationError,
    get_topic_for_subject,
    remaining_prompt_slots_for_subject,
)
from aperix_geo.services.prompts.taxonomy import PromptTaxonomyLock, prompt_taxonomy_lock
from aperix_geo.services.providers import LLMProviderError


def generate_subject_prompt_candidates(
    db: Session,
    *,
    subject: Subject,
    topic: Topic,
    count: int,
    taxonomy_lock: PromptTaxonomyLock,
) -> list[dict[str, str]]:
    """Call LLM and return up to ``count`` prompt rows for the topic (not persisted)."""
    remaining = remaining_prompt_slots_for_subject(db, subject.id)
    if remaining <= 0:
        raise PromptValidationError("提示词已达租户总量上限")

    assert_ai_usage_available(db, subject.tenant_id)

    take = min(count, remaining)
    ctx = prompt_context_from_subject(subject)
    profile = ctx["profile"]
    assert isinstance(profile, NicheProfile)
    existing_prompts = list(
        db.execute(
            select(Prompt.text).where(Prompt.subject_id == subject.id, Prompt.deleted.is_(False))
        ).scalars().all()
    )

    from aperix_geo.services.prompts.setup import generate_setup_prompts

    def _bill(stage: str, usage: dict) -> None:
        consume_ai_usage(
            db,
            tenant_id=subject.tenant_id,
            subject_id=subject.id,
            source="prompt",
            reference_id=usage_reference("prompt", subject.id, topic.id, take, stage),
            platform=SETUP_LLM_PLATFORM,
            usage=usage,
        )

    items = generate_setup_prompts(
        entity=str(ctx["entity"]),
        topics=[topic.name],
        industry=str(ctx["industry"]),
        features=str(ctx["features"]),
        customers=str(ctx["customers"]),
        competitors=[str(c) for c in ctx["competitors"] if str(c).strip()],
        aliases=[str(a) for a in ctx["aliases"] if str(a).strip()],
        profile=profile,
        prompts_per_topic=take,
        exclude_prompts=existing_prompts,
        on_live_call=_bill,
        taxonomy_lock=taxonomy_lock,
    )
    db.commit()

    generated = items[0]["prompts"] if items else []
    rows: list[dict[str, str]] = []
    for row in generated[:take]:
        text = str(row.get("text") or "").strip()
        if not text:
            continue
        rows.append(
            taxonomy_lock.apply_prompt_row(
                {
                    "text": text,
                    "funnel_stage": str(row.get("funnel_stage") or taxonomy_lock.funnel_stage),
                    "search_intent": str(row.get("search_intent") or taxonomy_lock.search_intent),
                    "decision_type": str(row.get("decision_type") or taxonomy_lock.decision_type),
                }
            )
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
    funnel_stage: str,
    search_intent: str,
    decision_type: str,
) -> list[dict[str, str]]:
    topic = get_topic_for_subject(db, subject_id, topic_id)
    lock = prompt_taxonomy_lock(
        funnel_stage=funnel_stage,
        search_intent=search_intent,
        decision_type=decision_type,
    )
    return generate_subject_prompt_candidates(
        db,
        subject=subject,
        topic=topic,
        count=count,
        taxonomy_lock=lock,
    )


def map_generate_error(exc: Exception) -> HTTPException:
    if isinstance(exc, LLMProviderError):
        return HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"提示词生成失败：{exc}",
        )
    if isinstance(exc, SubscriptionInactiveError):
        return subscription_inactive_http_exception(exc, detail="订阅已过期，无法生成提示词")
    if isinstance(exc, QuotaExceededError):
        return quota_exceeded_http_exception(exc)
    if isinstance(exc, PromptValidationError):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    if isinstance(exc, ValueError):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    raise exc
