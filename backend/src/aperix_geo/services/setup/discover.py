"""Setup discover：校验后入队 Celery 生成精简画像；竞品手填。"""

from __future__ import annotations

import logging
import time
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from aperix_geo.db.session import SessionLocal
from aperix_geo.utils.net import registrable_from
from aperix_geo.services.billing.quota import (
    assert_setup_ai_usage_available,
    charge_setup_ai_usage,
    usage_reference,
)
from aperix_geo.services.billing.usage_tokens import SETUP_LLM_PLATFORM
from aperix_geo.services.competitor.homepage import fetch_target_homepage
from aperix_geo.services.competitor.profile import (
    keywords_list,
    profile_from_dict,
    profile_to_dict,
)
from aperix_geo.services.competitor.topic_types import MAX_MONITORING_TOPICS
from aperix_geo.services.setup.cache import (
    create_session,
    get_profile_cache,
    get_session,
    set_profile_cache,
    update_session,
)
from aperix_geo.services.setup.cache.discover import (
    find_active_discover_session,
    set_discover_job,
)
from aperix_geo.services.setup.helpers import require_deepseek_api_key
from aperix_geo.services.setup.llm.stages import run_niche_profile_stage
from aperix_geo.services.setup.exceptions import MaterialsInsufficientError
from aperix_geo.services.setup.materials import (
    DiscoverProfileInputs,
    assert_brand_corpus_sufficient,
    assert_niche_profile_sufficient,
    build_user_corpus,
    materials_fingerprint,
    resolve_brand_materials,
)
from aperix_geo.services.setup.topic_items import setup_topics_from_names

logger = logging.getLogger(__name__)


def _topics_from_profile(profile_dict: dict[str, Any]) -> list[dict[str, str]]:
    names = keywords_list(profile_from_dict(profile_dict))[:MAX_MONITORING_TOPICS]
    return setup_topics_from_names(names)


def _assert_slim_profile_ok(profile_dict: dict[str, Any]) -> dict[str, str]:
    profile = profile_from_dict(profile_dict)
    assert_niche_profile_sufficient(profile)
    return profile_to_dict(profile)


def _resolve_target(
    *,
    subject_type: str,
    domain: str | None,
    brand: str | None,
) -> tuple[str, str]:
    if subject_type == "domain":
        if not domain:
            raise ValueError("domain is required for domain subject type")
        raw_website = domain.strip()
        target = registrable_from(raw_website)
        if not target:
            raise ValueError("invalid domain")
        return target, raw_website
    if not brand or not brand.strip():
        raise ValueError("brand is required for brand subject type")
    return brand.strip(), ""


def _session_matches_request(
    session: dict[str, Any],
    *,
    profile_hash: str,
    subject_type: str,
    target: str,
    region: str,
    language: str,
) -> bool:
    return (
        session.get("profile_hash") == profile_hash
        and session.get("subject_type") == subject_type
        and session.get("target") == target
        and session.get("region", "CN") == region
        and session.get("language", "zh-CN") == language
    )


def _fetch_homepage_inputs(*, fetch_target: str, user_url: str) -> tuple[str, tuple[tuple[str, str], ...]]:
    if not user_url.strip():
        return "", ()
    homepage = fetch_target_homepage(fetch_target, user_url=user_url)
    return (homepage.markdown or "").strip(), tuple(homepage.metadata.items())


def _profile_hash_for_start(
    *,
    subject_type: str,
    target: str,
    region: str,
    language: str,
    website_url: str,
    session: dict[str, Any] | None,
) -> tuple[str, str]:
    """不爬站：返回 (profile_hash, website_url_for_session)。"""
    from aperix_geo.services.setup.cache.profile import profile_hash

    if subject_type == "domain":
        url = website_url.strip()
        return (
            profile_hash(
                subject_type=subject_type,
                target=target,
                region=region,
                language=language,
                website_url=url,
            ),
            url,
        )

    if session is None:
        raise MaterialsInsufficientError("请先保存品牌资料后再进行分析。")
    if not session.get("materials_saved"):
        raise ValueError("materials not saved")
    materials = resolve_brand_materials(session)
    return (
        profile_hash(
            subject_type=subject_type,
            target=target,
            region=region,
            language=language,
            website_url=materials.website_url,
            materials_fingerprint=materials_fingerprint(materials),
        ),
        materials.website_url,
    )


def _prepare_profile_inputs(
    *,
    subject_type: str,
    target: str,
    website_url: str,
    session: dict[str, Any] | None,
) -> DiscoverProfileInputs:
    """统一准备画像 LLM 输入；品牌模式需已保存资料的 session（含爬站）。"""
    if subject_type == "domain":
        url = website_url.strip()
        homepage_text, homepage_metadata = _fetch_homepage_inputs(
            fetch_target=target,
            user_url=url or target,
        )
        return DiscoverProfileInputs(
            website_url=url,
            user_corpus="",
            homepage_text=homepage_text,
            homepage_metadata=homepage_metadata,
        )

    if session is None:
        raise MaterialsInsufficientError("请先保存品牌资料后再进行分析。")
    if not session.get("materials_saved"):
        raise ValueError("materials not saved")

    materials = resolve_brand_materials(session)
    url = materials.website_url
    homepage_text, homepage_metadata = _fetch_homepage_inputs(fetch_target=url, user_url=url)
    user_corpus = build_user_corpus(
        brand_intro=materials.brand_intro,
        upload_files=materials.upload_files,
    )
    assert_brand_corpus_sufficient(user_corpus=user_corpus, homepage_text=homepage_text)
    return DiscoverProfileInputs(
        website_url=url,
        user_corpus=user_corpus,
        homepage_text=homepage_text,
        homepage_metadata=homepage_metadata,
        materials_fingerprint=materials_fingerprint(materials),
        brand_intro=materials.brand_intro,
        upload_files=materials.upload_files,
        materials_saved=True,
    )


def _load_or_build_profile(
    *,
    db: Session,
    tenant_id: UUID,
    user_id: str,
    subject_type: str,
    target: str,
    region: str,
    language: str,
    profile_inputs: DiscoverProfileInputs,
    profile_hash: str,
) -> tuple[dict[str, Any], dict[str, Any], bool]:
    cached_profile = get_profile_cache(user_id=user_id, profile_hash=profile_hash)
    if cached_profile is not None:
        try:
            profile_dict = _assert_slim_profile_ok(cached_profile["profile"])
        except MaterialsInsufficientError as exc:
            logger.warning(
                "设置向导·发现 画像缓存校验未通过，重新生成 hash=%s: %s",
                profile_hash[:8],
                exc,
            )
        else:
            research_payload = dict(cached_profile["research_payload"])
            return profile_dict, research_payload, True

    assert_setup_ai_usage_available(db, tenant_id)
    profile, research_payload, usage = run_niche_profile_stage(
        subject_type=subject_type,
        target=target,
        region=region,
        language=language,
        website_url=profile_inputs.website_url,
        user_corpus=profile_inputs.user_corpus,
        homepage_text=profile_inputs.homepage_text,
        homepage_metadata=profile_inputs.homepage_metadata_dict,
    )
    if subject_type == "brand":
        assert_niche_profile_sufficient(profile)
    charge_setup_ai_usage(
        db,
        tenant_id=tenant_id,
        reference_id=usage_reference("niche_profile", profile_hash),
        platform=SETUP_LLM_PLATFORM,
        usage=usage,
    )
    db.commit()
    profile_dict = profile_to_dict(profile)
    set_profile_cache(
        user_id=user_id,
        profile_hash=profile_hash,
        profile=profile_dict,
        research_payload=research_payload,
    )
    return profile_dict, research_payload, False


def _apply_profile_to_session(
    *,
    user_id: str,
    session_id: str,
    subject_type: str,
    target: str,
    region: str,
    language: str,
    profile_hash_value: str,
    website_url: str,
    profile_dict: dict[str, Any],
    research_payload: dict[str, Any],
    session_for_materials: dict[str, Any] | None,
) -> None:
    topic_names = keywords_list(profile_from_dict(profile_dict))[:MAX_MONITORING_TOPICS]
    patch: dict[str, Any] = {
        "subject_type": subject_type,
        "target": target,
        "domain": target if subject_type == "domain" else None,
        "website_url": website_url or None,
        "brand": target if subject_type == "brand" else None,
        "region": region,
        "language": language,
        "profile_hash": profile_hash_value,
        "profile": profile_dict,
        "competitors": [],
        "monitoring_topics": topic_names,
        "research_payload": research_payload,
        "profile_summary": "",
    }
    if subject_type == "brand" and session_for_materials is not None:
        materials = resolve_brand_materials(session_for_materials)
        patch["brand_intro"] = materials.brand_intro
        patch["upload_files"] = list(materials.upload_files)
        patch["materials_saved"] = True
        patch["website_url"] = materials.website_url or website_url or None
    update_session(user_id=user_id, session_id=session_id, patch=patch)


def _empty_discover_response(session_id: str, *, status: str) -> dict[str, Any]:
    return {
        "session_id": session_id,
        "status": status,
    }


def start_discover_setup(
    *,
    db: Session,
    tenant_id: UUID,
    user_id: UUID,
    subject_type: str,
    domain: str | None,
    brand: str | None,
    region: str,
    language: str,
    session_id: str | None = None,
) -> dict[str, Any]:
    """校验后入队画像任务（或同步复用缓存）；立刻返回 session_id。"""
    require_deepseek_api_key()

    target, raw_website = _resolve_target(
        subject_type=subject_type,
        domain=domain,
        brand=brand,
    )

    from aperix_geo.services.subject.duplicate import assert_tenant_subject_unique

    assert_tenant_subject_unique(
        db,
        tenant_id=tenant_id,
        subject_type=subject_type,
        domain=target if subject_type == "domain" else "",
        brand=target if subject_type == "brand" else "",
    )

    user_key = str(user_id)
    sid = (session_id or "").strip()
    session_for_materials: dict[str, Any] | None = None
    if sid:
        session_for_materials = get_session(user_id=user_key, session_id=sid)

    profile_hash_value, website_url = _profile_hash_for_start(
        subject_type=subject_type,
        target=target,
        region=region,
        language=language,
        website_url=raw_website if subject_type == "domain" else "",
        session=session_for_materials if subject_type == "brand" else None,
    )

    # 会话画像可复用 → 同步 ready
    if sid and session_for_materials and _session_matches_request(
        session_for_materials,
        profile_hash=profile_hash_value,
        subject_type=subject_type,
        target=target,
        region=region,
        language=language,
    ):
        try:
            profile_dict = _assert_slim_profile_ok(dict(session_for_materials.get("profile") or {}))
        except MaterialsInsufficientError:
            profile_dict = None
        else:
            topic_names = keywords_list(profile_from_dict(profile_dict))[:MAX_MONITORING_TOPICS]
            update_session(
                user_id=user_key,
                session_id=sid,
                patch={
                    "profile": profile_dict,
                    "competitors": [],
                    "monitoring_topics": topic_names,
                },
            )
            set_discover_job(
                user_id=user_key,
                session_id=sid,
                status="ready",
                profile_hash=profile_hash_value,
            )
            logger.info("设置向导·发现 复用会话 session=%s", sid[:8])
            return _empty_discover_response(sid, status="ready")

    # 跨 session 画像缓存命中 → 同步落 session
    cached = get_profile_cache(user_id=user_key, profile_hash=profile_hash_value)
    if cached is not None:
        try:
            profile_dict = _assert_slim_profile_ok(cached["profile"])
        except MaterialsInsufficientError:
            profile_dict = None
        else:
            if subject_type == "brand":
                if not sid or session_for_materials is None:
                    raise MaterialsInsufficientError("请先保存品牌资料后再进行分析。")
                session_id_out = sid
            elif sid and session_for_materials is not None:
                session_id_out = sid
            else:
                session_id_out = create_session(
                    user_id=user_key,
                    payload={
                        "subject_type": subject_type,
                        "target": target,
                        "region": region,
                        "language": language,
                        "profile_hash": profile_hash_value,
                    },
                )
            _apply_profile_to_session(
                user_id=user_key,
                session_id=session_id_out,
                subject_type=subject_type,
                target=target,
                region=region,
                language=language,
                profile_hash_value=profile_hash_value,
                website_url=website_url,
                profile_dict=profile_dict,
                research_payload=dict(cached["research_payload"]),
                session_for_materials=session_for_materials,
            )
            set_discover_job(
                user_id=user_key,
                session_id=session_id_out,
                status="ready",
                profile_hash=profile_hash_value,
            )
            logger.info("设置向导·发现 命中画像缓存 session=%s", session_id_out[:8])
            return _empty_discover_response(session_id_out, status="ready")

    # 同 hash 已有进行中任务 → 复用
    active_sid = find_active_discover_session(user_id=user_key, profile_hash=profile_hash_value)
    if active_sid:
        logger.info("设置向导·发现 复用进行中任务 session=%s", active_sid[:8])
        return _empty_discover_response(active_sid, status="pending")

    assert_setup_ai_usage_available(db, tenant_id)

    # 确保 session
    if subject_type == "brand":
        if not sid or session_for_materials is None:
            raise MaterialsInsufficientError("请先保存品牌资料后再进行分析。")
        session_id_out = sid
        update_session(
            user_id=user_key,
            session_id=session_id_out,
            patch={
                "subject_type": subject_type,
                "target": target,
                "brand": target,
                "region": region,
                "language": language,
                "profile_hash": profile_hash_value,
                "website_url": website_url or None,
                "competitors": [],
                "monitoring_topics": [],
                "profile": {},
                "research_payload": {},
                "profile_summary": "",
            },
        )
    else:
        skeleton = {
            "subject_type": subject_type,
            "target": target,
            "domain": target,
            "website_url": website_url or None,
            "brand": None,
            "region": region,
            "language": language,
            "profile_hash": profile_hash_value,
            "profile": {},
            "competitors": [],
            "monitoring_topics": [],
            "research_payload": {},
            "profile_summary": "",
        }
        if sid and session_for_materials is not None:
            session_id_out = sid
            update_session(user_id=user_key, session_id=session_id_out, patch=skeleton)
        else:
            session_id_out = create_session(user_id=user_key, payload=skeleton)

    set_discover_job(
        user_id=user_key,
        session_id=session_id_out,
        status="pending",
        profile_hash=profile_hash_value,
    )

    from aperix_geo.tasks.setup import setup_discover_profile

    setup_discover_profile.delay(
        user_id=user_key,
        tenant_id=str(tenant_id),
        session_id=session_id_out,
        subject_type=subject_type,
        target=target,
        region=region,
        language=language,
        website_url=website_url if subject_type == "domain" else "",
        profile_hash=profile_hash_value,
    )
    logger.info(
        "设置向导·发现 已入队 session=%s type=%s target=%r",
        session_id_out[:8],
        subject_type,
        target,
    )
    return _empty_discover_response(session_id_out, status="pending")


def run_discover_setup_job(
    *,
    user_id: str,
    tenant_id: UUID,
    session_id: str,
    subject_type: str,
    target: str,
    region: str,
    language: str,
    website_url: str,
    profile_hash: str,
) -> None:
    """Celery worker：爬站 + LLM + 写 session。"""
    t0 = time.perf_counter()
    set_discover_job(
        user_id=user_id,
        session_id=session_id,
        status="running",
        profile_hash=profile_hash,
    )
    session = get_session(user_id=user_id, session_id=session_id)
    if session is None:
        set_discover_job(
            user_id=user_id,
            session_id=session_id,
            status="failed",
            profile_hash=profile_hash,
            error="setup session not found",
        )
        return

    db = SessionLocal()
    try:
        profile_inputs = _prepare_profile_inputs(
            subject_type=subject_type,
            target=target,
            website_url=website_url if subject_type == "domain" else "",
            session=session if subject_type == "brand" else None,
        )
        profile_dict, research_payload, from_cache = _load_or_build_profile(
            db=db,
            tenant_id=tenant_id,
            user_id=user_id,
            subject_type=subject_type,
            target=target,
            region=region,
            language=language,
            profile_inputs=profile_inputs,
            profile_hash=profile_hash,
        )
        _apply_profile_to_session(
            user_id=user_id,
            session_id=session_id,
            subject_type=subject_type,
            target=target,
            region=region,
            language=language,
            profile_hash_value=profile_hash,
            website_url=profile_inputs.website_url,
            profile_dict=profile_dict,
            research_payload=research_payload,
            session_for_materials=session if subject_type == "brand" else None,
        )
        set_discover_job(
            user_id=user_id,
            session_id=session_id,
            status="ready",
            profile_hash=profile_hash,
        )
        logger.info(
            "设置向导·发现 job 完成 session=%s 耗时=%.1fs 缓存=%s",
            session_id[:8],
            time.perf_counter() - t0,
            from_cache,
        )
    except MaterialsInsufficientError as exc:
        db.rollback()
        set_discover_job(
            user_id=user_id,
            session_id=session_id,
            status="failed",
            profile_hash=profile_hash,
            error=exc.message,
        )
        logger.warning("设置向导·发现 job 资料不足 session=%s: %s", session_id[:8], exc)
    except Exception as exc:
        db.rollback()
        set_discover_job(
            user_id=user_id,
            session_id=session_id,
            status="failed",
            profile_hash=profile_hash,
            error=str(exc) or "画像生成失败",
        )
        logger.exception("设置向导·发现 job 失败 session=%s", session_id[:8])
        raise
    finally:
        db.close()
