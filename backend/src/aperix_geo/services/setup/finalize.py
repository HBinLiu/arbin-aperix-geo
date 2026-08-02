"""设置向导：一次性落库 subject + 竞品 + 主题 + 提示词 + 采样任务。"""

from __future__ import annotations

import logging
import time

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
from aperix_geo.services.billing.exceptions import QuotaExceededError, SubscriptionInactiveError
from aperix_geo.services.billing.http import billing_http_exception
from aperix_geo.services.billing.quota import (
    assert_can_add_prompts,
    assert_can_create_subject,
    assert_platform_capacity,
    get_limits_for_enforcement,
    tenant_has_usable_subscription,
)
from aperix_geo.services.competitor.enrich import enrich_confirmed_competitors
from aperix_geo.services.competitor.types import SiteHead
from aperix_geo.services.competitor.persist import apply_competitors
from aperix_geo.services.prompts.taxonomy import (
    normalize_decision_type,
    normalize_funnel_stage,
    normalize_search_intent,
)
from aperix_geo.services.setup.topic_items import topic_name_key
from aperix_geo.services.brand.sync import sync_subject_brands_from_setup
from aperix_geo.services.sampling.platforms import resolve_subject_sampling_platforms
from aperix_geo.services.sampling.workflow.jobs import create_and_enqueue_sampling_job
from aperix_geo.services.setup.cache import delete_session, get_session
from aperix_geo.services.knowledge.persist import persist_brand_knowledge_from_setup
from aperix_geo.services.setup.helpers import (
    company_from_session,
    confirmed_competitors_from_session,
    enrich_subject_aliases,
    profile_summary_from_session,
    subject_summary_from_session,
    validate_confirmed_competitors,
)
from aperix_geo.services.subject.domain_fields import apply_subject_domain_fields
from aperix_geo.services.subject.rules import validate_brand_competitors, validate_subject_fields
from aperix_geo.utils.net import ensure_brand, registrable_from
from aperix_geo.utils.text import prompt_text_hash

logger = logging.getLogger(__name__)


def finalize_setup(
    db: Session,
    *,
    user: User,
    session_id: str,
    body: SetupFinalizeBody,
) -> tuple[Subject, SamplingJob | None, bool]:
    t0 = time.perf_counter()
    setup_session_id = session_id.strip()
    setup_session = get_session(user_id=str(user.id), session_id=setup_session_id)
    if setup_session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="setup session not found")

    knowledge_ready = False
    st = SubjectType(setup_session["subject_type"])
    target = str(setup_session.get("target") or "").strip()
    prompt_count = sum(len(topic.prompts) for topic in body.topics)
    logger.info(
        "设置向导·落库 开始 session=%s type=%s target=%r 主题=%d 问句=%d",
        setup_session_id[:8],
        st.value,
        target,
        len(body.topics),
        prompt_count,
    )
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
    if st == SubjectType.brand and website_url:
        domain = registrable_from(website_url) or ""

    topic_items = [t for t in body.topics if t.name.strip()]
    if not topic_items:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="至少需要一个主题")

    prompt_count = sum(1 for t in topic_items for p in t.prompts if p.text.strip())
    if prompt_count < 1:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="至少需要一条提示词")

    try:
        assert_can_create_subject(db, user.tenant_id)
        assert_can_add_prompts(db, user.tenant_id, count=prompt_count)
    except (SubscriptionInactiveError, QuotaExceededError) as exc:
        raise billing_http_exception(exc, inactive_detail="订阅已过期，无法完成设置") from exc

    subscribed = tenant_has_usable_subscription(db, user.tenant_id)

    try:
        session_competitors = confirmed_competitors_from_session(setup_session)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    try:
        validate_confirmed_competitors(subject_type=st.value, competitors=session_competitors)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    heads_cache: dict[str, SiteHead] = {}
    subject_reg = registrable_from(domain) if st == SubjectType.domain else ""
    extra_urls = {subject_reg: website_url} if subject_reg and website_url else {}
    enriched_competitors = enrich_confirmed_competitors(
        session_competitors,
        session=setup_session,
        extra_head_domains=[subject_reg] if subject_reg else None,
        extra_preferred_urls=extra_urls or None,
        heads_out=heads_cache,
    )
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
    aliases = enrich_subject_aliases(
        brand=brand,
        domain=domain,
        session=setup_session,
        heads=heads_cache,
    )
    niche_profile_data = dict(setup_session.get("profile") or {})
    plan_limits = get_limits_for_enforcement(db, user.tenant_id)

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
        sampling_frequency=plan_limits.sampling_frequency,
        # Defer auto-sampling until a subscription is active.
        sampling_enabled=subscribed,
    )
    validate_subject_fields(subject)
    try:
        apply_competitors(db, subject, competitors=competitors_for_persist)
    except (SubscriptionInactiveError, QuotaExceededError) as exc:
        raise billing_http_exception(exc, inactive_detail="订阅已过期，无法完成设置") from exc
    validate_brand_competitors(subject)

    db.add(subject)
    db.flush()
    sync_subject_brands_from_setup(db, subject=subject)

    if st == SubjectType.brand:
        knowledge = persist_brand_knowledge_from_setup(
            db,
            subject=subject,
            setup_session=setup_session,
            user_id=user.id,
        )
        knowledge_ready = knowledge is not None

    platforms = resolve_subject_sampling_platforms(subject)
    if not platforms:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No LLM providers configured for sampling (set at least one *_API_KEY)",
        )
    try:
        assert_platform_capacity(db, user.tenant_id, len(platforms))
    except (SubscriptionInactiveError, QuotaExceededError) as exc:
        db.rollback()
        raise billing_http_exception(exc, inactive_detail="订阅已过期，无法完成设置") from exc

    topics: list[Topic] = []
    for item in topic_items:
        topic = Topic(
            subject_id=subject.id,
            name=item.name.strip(),
        )
        db.add(topic)
        db.flush()
        topics.append(topic)

    seen_hashes: set[str] = set()
    prompts: list[Prompt] = []
    topic_by_key = {topic_name_key(t.name): t for t in topics}
    for topic_item in topic_items:
        topic = topic_by_key.get(topic_name_key(topic_item.name.strip()))
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
                decision_type=normalize_decision_type(prompt_item.decision_type),
                enabled=True,
            )
            db.add(prompt)
            prompts.append(prompt)

    if not prompts:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="至少需要一条提示词")

    db.flush()

    job: SamplingJob | None = None
    if subscribed:
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
        "设置向导·落库 完成 session=%s 耗时=%.1fs subject=%s 主题=%d 问句=%d 别名=%d job=%s",
        setup_session_id[:8],
        time.perf_counter() - t0,
        subject.id,
        len(topics),
        len(prompts),
        len(aliases),
        job.id if job else None,
    )
    return subject, job, knowledge_ready
