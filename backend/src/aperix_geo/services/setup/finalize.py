"""设置向导：一次性落库 subject + 竞品 + 主题 + 提示词 + 采样任务。"""

from __future__ import annotations

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
from aperix_geo.schemas.catalog import SetupFinalizeRequest
from aperix_geo.services.competitor.persist import apply_competitors
from aperix_geo.services.sampling.jobs import create_and_enqueue_sampling_job
from aperix_geo.services.sampling.schedule import DEFAULT_SAMPLING_INTERVAL_HOURS
from aperix_geo.services.sampling.subject import resolve_subject_sampling_platforms
from aperix_geo.services.setup.helpers import (
    company_from_setup_session,
    profile_summary_from_setup_session,
)
from aperix_geo.services.subject.domain_fields import apply_subject_domain_fields
from aperix_geo.utils.domains import ensure_brand
from aperix_geo.services.subject.rules import validate_brand_competitors, validate_subject_fields
from aperix_geo.utils.coerce import normalize_monitoring_scope
from aperix_geo.utils.text import prompt_text_hash


def finalize_setup(
    db: Session,
    *,
    user: User,
    body: SetupFinalizeRequest,
) -> tuple[Subject, SamplingJob]:
    st = SubjectType(body.type.value)
    domain_val = body.domain.strip() if body.domain else ""
    domain, website_url = apply_subject_domain_fields(
        subject_type=st,
        raw_domain=domain_val,
    )

    topic_items = [t for t in body.topics if t.name.strip()]
    if not topic_items:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="至少需要一个主题")

    prompt_count = sum(1 for t in topic_items for p in t.prompts if p.strip())
    if prompt_count < 1:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="至少需要一条提示词")

    if st == SubjectType.domain and not any((c.domain or "").strip() for c in body.competitors):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="按网站监测时至少需要一个竞品域名")
    if st == SubjectType.brand and not any(
        (c.brand or "").strip() and not (c.domain or "").strip() for c in body.competitors
    ):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="按品牌监测时至少需要一个竞品品牌")

    setup_session_id = body.setup_session_id.strip() if body.setup_session_id else None
    profile_company = company_from_setup_session(
        user_id=str(user.id),
        setup_session_id=setup_session_id,
    )
    brand = ensure_brand(
        profile_company or (body.brand.strip() if body.brand else ""),
        domain=domain if st == SubjectType.domain else None,
    )

    subject = Subject(
        tenant_id=user.tenant_id,
        type=st,
        domain=domain,
        brand=brand,
        website_url=website_url,
        aliases=[],
        monitoring_scope=normalize_monitoring_scope(
            body.monitoring_scope.model_dump(exclude_none=True) if body.monitoring_scope else None
        ),
        profile_summary=profile_summary_from_setup_session(
            user_id=str(user.id),
            setup_session_id=setup_session_id,
        ),
        sampling_interval=DEFAULT_SAMPLING_INTERVAL_HOURS,
    )
    validate_subject_fields(subject)
    apply_competitors(subject, competitors=body.competitors)
    validate_brand_competitors(subject)

    db.add(subject)
    db.flush()

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
    for item in topic_items:
        topic = topic_by_name.get(item.name.strip())
        if not topic:
            continue
        for raw in item.prompts:
            text = raw.strip()
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
    return subject, job
