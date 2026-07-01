"""Setup discover：微观利基画像 + 竞品发现（不含监测主题）。"""

from __future__ import annotations

import logging
import time
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from aperix_geo.utils.net import registrable_from
from aperix_geo.services.billing.quota import assert_ai_usage_available, consume_ai_usage, usage_reference
from aperix_geo.services.billing.usage_tokens import SETUP_LLM_PLATFORM
from aperix_geo.services.competitor.homepage import fetch_target_homepage
from aperix_geo.services.competitor.profile import profile_from_dict, profile_to_dict, search_queries_list
from aperix_geo.services.setup.cache import (
    create_session,
    get_profile_cache,
    get_session,
    set_profile_cache,
    update_session,
)
from aperix_geo.services.setup.competitors import (
    competitors_for_api_response,
    discover_competitors_for_session,
)
from aperix_geo.services.setup.helpers import require_deepseek_api_key
from aperix_geo.services.setup.llm.stages import run_niche_profile_stage
from aperix_geo.services.setup.profile_qa import sanitize_profile_lexicon, validate_profile_lexicon
from aperix_geo.services.setup.exceptions import MaterialsInsufficientError
from aperix_geo.services.setup.materials import (
    DiscoverProfileInputs,
    assert_brand_corpus_sufficient,
    assert_niche_profile_sufficient,
    build_user_corpus,
    materials_fingerprint,
    resolve_brand_materials,
)

logger = logging.getLogger(__name__)


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


def _prepare_profile_inputs(
    *,
    subject_type: str,
    target: str,
    website_url: str,
    session: dict[str, Any] | None,
) -> DiscoverProfileInputs:
    """统一准备画像 LLM 输入；品牌模式需已保存资料的 session。"""
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
) -> tuple[dict[str, Any], dict[str, Any], list[str], bool]:
    cached_profile = get_profile_cache(user_id=user_id, profile_hash=profile_hash)
    if cached_profile is not None:
        profile_dict = cached_profile["profile"]
        try:
            sanitized = sanitize_profile_lexicon(profile_from_dict(profile_dict))
            validate_profile_lexicon(sanitized)
            profile_dict = profile_to_dict(sanitized)
        except ValueError as exc:
            logger.warning(
                "设置向导·发现 画像缓存校验未通过，重新生成 hash=%s: %s",
                profile_hash[:8],
                exc,
            )
        else:
            research_payload = dict(cached_profile["research_payload"])
            search_queries = search_queries_list(profile_from_dict(profile_dict)) or (
                [target] if target else []
            )
            return profile_dict, research_payload, search_queries, True

    assert_ai_usage_available(db, tenant_id)
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
    consume_ai_usage(
        db,
        tenant_id=tenant_id,
        source="setup",
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
    search_queries = search_queries_list(profile) or ([target] if target else [])
    return profile_dict, research_payload, search_queries, False


def discover_setup(
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
    """建立微观画像并完成竞品发现；可选 session_id 用于退回后缓存命中。"""
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

    profile_inputs = _prepare_profile_inputs(
        subject_type=subject_type,
        target=target,
        website_url=raw_website if subject_type == "domain" else "",
        session=session_for_materials if subject_type == "brand" else None,
    )
    profile_hash_value = profile_inputs.profile_hash_value(
        subject_type=subject_type,
        target=target,
        region=region,
        language=language,
    )

    existing: dict[str, Any] | None = None
    if sid and session_for_materials and _session_matches_request(
        session_for_materials,
        profile_hash=profile_hash_value,
        subject_type=subject_type,
        target=target,
        region=region,
        language=language,
    ):
        try:
            sanitized = sanitize_profile_lexicon(
                profile_from_dict(dict(session_for_materials.get("profile") or {}))
            )
            validate_profile_lexicon(sanitized)
        except ValueError as exc:
            logger.warning(
                "设置向导·发现 会话画像校验未通过，重新生成 session=%s: %s",
                sid[:8],
                exc,
            )
        else:
            existing = session_for_materials

    t0 = time.perf_counter()
    if existing is not None:
        session_id = sid
        profile_dict = dict(existing.get("profile") or {})
        search_queries = list(existing.get("search_queries") or [])
        if not existing.get("research_payload"):
            cached_profile = get_profile_cache(user_id=user_key, profile_hash=profile_hash_value)
            if cached_profile and cached_profile.get("research_payload"):
                update_session(
                    user_id=user_key,
                    session_id=session_id,
                    patch={"research_payload": dict(cached_profile["research_payload"])},
                )
        logger.info(
            "设置向导·发现 复用会话 session=%s target=%r",
            session_id[:8],
            target,
        )
    else:
        profile_dict, research_payload, search_queries, from_cache = _load_or_build_profile(
            db=db,
            tenant_id=tenant_id,
            user_id=user_key,
            subject_type=subject_type,
            target=target,
            region=region,
            language=language,
            profile_inputs=profile_inputs,
            profile_hash=profile_hash_value,
        )
        session_payload: dict[str, Any] = {
            "subject_type": subject_type,
            "target": target,
            "domain": target if subject_type == "domain" else None,
            "website_url": profile_inputs.website_url or None,
            "brand": target if subject_type == "brand" else None,
            "region": region,
            "language": language,
            "profile_hash": profile_hash_value,
            "profile": profile_dict,
            "search_queries": search_queries,
            "monitoring_topics": [],
            "topic_clusters": [],
            "research_payload": research_payload,
            "profile_summary": "",
        }
        if subject_type == "brand":
            session_payload["brand_intro"] = profile_inputs.brand_intro
            session_payload["upload_files"] = list(profile_inputs.upload_files)
            session_payload["materials_saved"] = profile_inputs.materials_saved
        if sid and session_for_materials is not None:
            session_id = sid
            update_session(user_id=user_key, session_id=session_id, patch=session_payload)
        else:
            session_id = create_session(user_id=user_key, payload=session_payload)
        logger.info(
            "设置向导·发现 新建会话 session=%s target=%r type=%s 画像缓存=%s",
            session_id[:8],
            target,
            subject_type,
            from_cache,
        )

    competitors = discover_competitors_for_session(
        user_id=user_id,
        session_id=session_id,
        profile_dict=profile_dict,
        search_queries=search_queries,
    )

    logger.info(
        "设置向导·发现 完成 session=%s 耗时=%.1fs 竞品=%d",
        session_id[:8],
        time.perf_counter() - t0,
        len(competitors),
    )
    return {
        "session_id": session_id,
        "competitors": competitors_for_api_response(competitors),
    }
