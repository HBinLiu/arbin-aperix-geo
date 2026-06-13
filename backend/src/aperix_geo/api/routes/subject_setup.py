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
from aperix_geo.services.providers import LLMProviderError
from aperix_geo.services.setup.discover import discover_competitors_from_session, discover_profile
from aperix_geo.services.setup.finalize import finalize_setup
from aperix_geo.services.setup.cache import generate_setup_prompts_for_session

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
            monitoring_topics=body.monitoring_topics,
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
    try:
        items = generate_setup_prompts_for_session(
            user_id=str(current.id),
            session_id=body.session_id.strip(),
            topics=body.topics,
            competitors=body.competitors,
            exclude_prompts=body.exclude_prompts,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except (LLMProviderError, json.JSONDecodeError, TypeError) as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"提示词生成失败：{e}",
        ) from e
    return GeneratePromptsResponse(items=[TopicPromptsOut(**row) for row in items])


@router.post("/setup-finalize", response_model=SetupFinalizeResponse, status_code=status.HTTP_201_CREATED)
def setup_finalize_endpoint(
    body: SetupFinalizeRequest,
    db: DbSession,
    current: CurrentUser,
) -> SetupFinalizeResponse:
    subject, job = finalize_setup(db, user=current, body=body)
    return SetupFinalizeResponse(subject=subject, sampling_job_id=job.id)
