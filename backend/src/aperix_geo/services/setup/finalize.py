"""设置向导：一次性落库 subject + 竞品 + 主题 + 提示词 + 采样任务。"""

from __future__ import annotations

import logging

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from aperix_geo.db.models import (
    Prompt,
    SamplingJob,
    Subject,
    SubjectType,
    Topic,
    User,
)
from aperix_geo.schemas.catalog import CompetitorItem, SetupFinalizeBody
from aperix_geo.services.competitor.persist import apply_competitors
from aperix_geo.services.prompts.taxonomy import normalize_funnel_stage, normalize_search_intent
from aperix_geo.services.brand.sync import sync_subject_brands_from_setup
from aperix_geo.services.sampling.platforms import resolve_subject_sampling_platforms
from aperix_geo.services.sampling.workflow.jobs import create_and_enqueue_sampling_job
from aperix_geo.services.setup.cache import delete_session, get_session
from aperix_geo.services.competitor.enrich import enrich_confirmed_competitors
from aperix_geo.services.setup.helpers import (
    company_from_session,
    confirmed_competitors_from_session,
    profile_summary_from_session,
    subject_aliases_from_session,
    subject_summary_from_session,
    validate_confirmed_competitors,
)
from aperix_geo.services.subject.domain_fields import apply_subject_domain_fields
from aperix_geo.services.subject.rules import validate_brand_competitors, validate_subject_fields
from aperix_geo.utils.net import ensure_brand
from aperix_geo.utils.text import prompt_text_hash

logger = logging.getLogger(__name__)


def finalize_setup(
    db: Session,
    *,
    user: User,
    session_id: str,
    body: SetupFinalizeBody,
) -> tuple[Subject, SamplingJob]:
    setup_session_id = session_id.strip()
    setup_session = get_session(user_id=str(user.id), session_id=setup_session_id)
    if setup_session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="setup session not found")

    st = SubjectType(setup_session["subject_type"])
    if st == SubjectType.domain:
        raw_domain = str(setup_session.get("domain") or setup_session.get("target") or "").strip()
        raw_website = str(setup_session.get("website_url") or setup_session.get("domain") or "").strip()
    else:
        raw_domain = ""
        raw_website = str(setup_session.get("website_url") or "").strip()
    domain, website_url = apply_subject_domain_fields(
        subject_type=st,
        raw_domain=raw_domain,
        raw_website_url=raw_website,
    )

    topic_items = [t for t in body.topics if t.name.strip()]
    if not topic_items:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="至少需要一个主题")

    prompt_count = sum(1 for t in topic_items for p in t.prompts if p.text.strip())
    if prompt_count < 1:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="至少需要一条提示词")

    try:
        session_competitors = confirmed_competitors_from_session(setup_session)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    try:
        validate_confirmed_competitors(subject_type=st.value, competitors=session_competitors)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    enriched_competitors = enrich_confirmed_competitors(session_competitors, session=setup_session)
    competitors_for_persist = [
        CompetitorItem(
            domain=str(row.get("domain") or ""),
            website_url=str(row.get("website_url") or ""),
            brand=str(row.get("brand") or ""),
            summary=str(row.get("summary") or ""),
            aliases=list(row.get("aliases") or []),
            cross_validate_score=(
                float(row["cross_validate_score"])
                if row.get("cross_validate_score") is not None
                else None
            ),
            cross_validate_reason=str(row.get("cross_validate_reason") or ""),
        )
        for row in enriched_competitors
    ]

    profile_company = company_from_session(setup_session)
    brand_from_session = str(setup_session.get("brand") or "").strip()
    brand = ensure_brand(
        profile_company or brand_from_session,
        domain=domain if st == SubjectType.domain else None,
    )
    aliases = subject_aliases_from_session(setup_session)
    niche_profile_data = dict(setup_session.get("profile") or {})

    subject = Subject(
        tenant_id=user.tenant_id,
        type=st,
        domain=domain,
        brand=brand,
        website_url=website_url,
        aliases=aliases,
        profile_summary=profile_summary_from_session(setup_session),
        summary=subject_summary_from_session(setup_session),
        niche_profile=niche_profile_data,
    )
    validate_subject_fields(subject)
    apply_competitors(subject, competitors=competitors_for_persist)
    validate_brand_competitors(subject)

    db.add(subject)
    db.flush()
    sync_subject_brands_from_setup(db, subject=subject)

    platforms = resolve_subject_sampling_platforms(subject)
    if not platforms:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No LLM providers configured for sampling (set at least one *_API_KEY)",
        )

    topics: list[Topic] = []
    for item in topic_items:
        topic = Topic(subject_id=subject.id, name=item.name.strip())
        db.add(topic)
        db.flush()
        topics.append(topic)

    seen_hashes: set[str] = set()
    prompts: list[Prompt] = []
    topic_by_name = {t.name: t for t in topics}
    for topic_item in topic_items:
        topic = topic_by_name.get(topic_item.name.strip())
        if not topic:
            continue
        for prompt_item in topic_item.prompts:
            text = prompt_item.text.strip()
            if not text:
                continue
            th = prompt_text_hash(text)
            if th in seen_hashes:
                continue
            seen_hashes.add(th)
            prompt = Prompt(
                subject_id=subject.id,
                topic_id=topic.id,
                text=text,
                text_hash=th,
                funnel_stage=normalize_funnel_stage(prompt_item.funnel_stage),
                search_intent=normalize_search_intent(prompt_item.search_intent),
                enabled=True,
            )
            db.add(prompt)
            prompts.append(prompt)

    if not prompts:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="至少需要一条提示词")

    db.flush()

    job = create_and_enqueue_sampling_job(
        db,
        subject=subject,
        tenant_id=user.tenant_id,
        platforms=platforms,
        update_schedule_anchor=True,
    )
    db.refresh(subject)
    delete_session(user_id=str(user.id), session_id=setup_session_id)
    logger.info(
        "设置向导·落库 完成 session=%s subject=%s 主题=%d 问句=%d 别名=%d",
        setup_session_id[:8],
        subject.id,
        len(topics),
        len(prompts),
        len(aliases),
    )
    return subject, job
