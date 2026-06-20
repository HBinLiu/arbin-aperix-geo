"""Subject 设置向导 API。

向导 UI 四步，后端 4 个接口；`session_id` 放在 body 中传递。

| UI Step | API |
|---------|-----|
| 0 设置 → 1 选竞品 | `POST /subjects/setup/discover` |
| 1 选竞品 → 2 审主题 | `POST /subjects/setup/topics`（携带确认后的竞品） |
| 2 审主题 → 3 提示词 | `POST /subjects/setup/prompts` |
| 3 提示词 → 完成 | `POST /subjects/setup/finalize` |
"""

import json

from fastapi import APIRouter, HTTPException, status

from aperix_geo.api.deps import CurrentUser, DbSession
from aperix_geo.schemas.catalog import (
    SetupDiscoverRequest,
    SetupDiscoverResponse,
    SetupFinalizeBody,
    SetupFinalizeResponse,
    SetupPromptsGenerateRequest,
    SetupPromptsGenerateResponse,
    SetupTopicsRequest,
    SetupTopicsResponse,
    TopicPromptsOut,
)
from aperix_geo.services.providers import LLMProviderError
from aperix_geo.services.setup.prompts import generate_setup_prompts_for_session
from aperix_geo.services.setup.discover import discover_setup
from aperix_geo.services.setup.finalize import finalize_setup
from aperix_geo.services.setup.topics import run_setup_topics_step

router = APIRouter(prefix="/setup", tags=["setup"])


@router.post("/discover", response_model=SetupDiscoverResponse)
def discover_setup_endpoint(
    body: SetupDiscoverRequest,
    current: CurrentUser,
) -> SetupDiscoverResponse:
    try:
        result = discover_setup(
            user_id=current.id,
            session_id=body.session_id,
            subject_type=body.type.value,
            domain=body.domain.strip() if body.domain else None,
            brand=body.brand.strip() if body.brand else None,
            region=body.region,
            language=body.language,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    except (LLMProviderError, json.JSONDecodeError, TypeError) as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"画像或竞品发现失败：{e}",
        ) from e
    return SetupDiscoverResponse(**result)


@router.post("/topics", response_model=SetupTopicsResponse)
def generate_setup_topics_endpoint(
    body: SetupTopicsRequest,
    current: CurrentUser,
) -> SetupTopicsResponse:
    try:
        topics = run_setup_topics_step(
            user_id=str(current.id),
            session_id=body.session_id.strip(),
            competitors=body.competitors,
        )
    except ValueError as e:
        status_code = status.HTTP_404_NOT_FOUND if "not found" in str(e) else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=status_code, detail=str(e)) from e
    except (LLMProviderError, json.JSONDecodeError, TypeError) as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"监测主题生成失败：{e}",
        ) from e
    return SetupTopicsResponse(monitoring_topics=topics)


@router.post("/prompts", response_model=SetupPromptsGenerateResponse)
def generate_setup_prompts_endpoint(
    body: SetupPromptsGenerateRequest,
    current: CurrentUser,
) -> SetupPromptsGenerateResponse:
    try:
        items = generate_setup_prompts_for_session(
            user_id=str(current.id),
            session_id=body.session_id.strip(),
            topics=body.topics,
            exclude_prompts=body.exclude_prompts,
        )
    except ValueError as e:
        status_code = status.HTTP_404_NOT_FOUND if "not found" in str(e) else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=status_code, detail=str(e)) from e
    except (LLMProviderError, json.JSONDecodeError, TypeError) as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"提示词生成失败：{e}",
        ) from e
    return SetupPromptsGenerateResponse(items=[TopicPromptsOut(**row) for row in items])


@router.post("/finalize", response_model=SetupFinalizeResponse, status_code=status.HTTP_201_CREATED)
def setup_finalize_endpoint(
    body: SetupFinalizeBody,
    db: DbSession,
    current: CurrentUser,
) -> SetupFinalizeResponse:
    subject, job = finalize_setup(
        db,
        user=current,
        session_id=body.session_id.strip(),
        body=body,
    )
    return SetupFinalizeResponse(subject_id=subject.id, sampling_job_id=job.id)
