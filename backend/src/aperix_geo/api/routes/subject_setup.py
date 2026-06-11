"""Subject 设置向导 API。"""

import json

from fastapi import APIRouter, HTTPException, status

from aperix_geo.api.deps import CurrentUser, DbSession
from aperix_geo.schemas.catalog import (
    DiscoverCompetitorsResponse,
    DiscoverCompetitorsSearchRequest,
    DiscoverProfileRequest,
    DiscoverProfileResponse,
    GeneratePromptsRequest,
    GeneratePromptsResponse,
    SetupFinalizeRequest,
    SetupFinalizeResponse,
    TopicPromptsOut,
)
from aperix_geo.services.competitor.profile import profile_from_dict
from aperix_geo.services.prompts.context import entity_aliases
from aperix_geo.services.providers import LLMProviderError
from aperix_geo.services.prompts import generate_setup_prompts
from aperix_geo.services.setup.discover import discover_competitors_from_session, discover_profile
from aperix_geo.services.setup.finalize import finalize_setup
from aperix_geo.services.setup.session import get_session

router = APIRouter()


@router.post("/discover-profile", response_model=DiscoverProfileResponse)
def discover_profile_endpoint(
    body: DiscoverProfileRequest,
    current: CurrentUser,
) -> DiscoverProfileResponse:
    try:
        result = discover_profile(
            user_id=current.id,
            subject_type=body.type.value,
            domain=body.domain.strip() if body.domain else None,
            brand=body.brand.strip() if body.brand else None,
            region=body.region,
            language=body.language,
        )
    except (LLMProviderError, ValueError, json.JSONDecodeError, TypeError) as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"微观利基画像失败：{e}",
        ) from e
    return DiscoverProfileResponse(**result)


@router.post("/discover-competitors", response_model=DiscoverCompetitorsResponse)
def discover_competitors_endpoint(
    body: DiscoverCompetitorsSearchRequest,
    current: CurrentUser,
) -> DiscoverCompetitorsResponse:
    try:
        result = discover_competitors_from_session(
            user_id=current.id,
            session_id=body.session_id.strip(),
            micro_keywords=body.micro_keywords,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except (LLMProviderError, json.JSONDecodeError, TypeError) as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"竞品搜索失败：{e}",
        ) from e
    return DiscoverCompetitorsResponse(**result)


@router.post("/generate-prompts", response_model=GeneratePromptsResponse)
def generate_prompts_endpoint(
    body: GeneratePromptsRequest,
    current: CurrentUser,
) -> GeneratePromptsResponse:
    session = get_session(user_id=str(current.id), session_id=body.session_id.strip())
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="setup session not found or expired")

    entity = str(session.get("target") or "").strip()
    if not entity:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="setup session missing target")

    profile = profile_from_dict(session.get("profile") or {})

    items = generate_setup_prompts(
        entity=entity,
        topics=body.topics,
        industry=profile.get("industry", ""),
        core_features=profile.get("core_features", ""),
        target_customers=profile.get("target_customers", ""),
        competitors=body.competitors,
        aliases=entity_aliases(
            entity=entity,
            profile_company=str(profile.get("company") or ""),
        ),
        exclude_prompts=body.exclude_prompts,
    )
    return GeneratePromptsResponse(items=[TopicPromptsOut(**row) for row in items])


@router.post("/setup-finalize", response_model=SetupFinalizeResponse, status_code=status.HTTP_201_CREATED)
def setup_finalize_endpoint(
    body: SetupFinalizeRequest,
    db: DbSession,
    current: CurrentUser,
) -> SetupFinalizeResponse:
    subject, job = finalize_setup(db, user=current, body=body)
    return SetupFinalizeResponse(subject=subject, sampling_job_id=job.id)
