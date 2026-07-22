"""Subject 设置向导 API。

域名模式：4 步 UI（discover → topics → prompts → finalize）。
品牌模式：5 步 UI（session → materials → discover → …）；`session_id` 放在 body 中传递。
"""

import json

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from aperix_geo.api.deps import CurrentUser, DbSession
from aperix_geo.schemas.catalog import (
    SetupDiscoverRequest,
    SetupDiscoverResponse,
    SetupFinalizeBody,
    SetupFinalizeResponse,
    SetupMaterialsSaveRequest,
    SetupMaterialsSaveResponse,
    SetupPromptsGenerateRequest,
    SetupPromptsGenerateResponse,
    SetupSessionCreateRequest,
    SetupSessionCreateResponse,
    SetupMonitoringTopicOut,
    SetupTopicsRequest,
    SetupTopicsResponse,
    SetupUploadFileOut,
    TopicPromptsOut,
)
from aperix_geo.services.providers import LLMProviderError
from aperix_geo.services.billing.exceptions import QuotaExceededError
from aperix_geo.services.billing.http import quota_exceeded_http_exception
from aperix_geo.services.setup.prompts import generate_setup_prompts_for_session
from aperix_geo.services.setup.discover import discover_setup
from aperix_geo.services.setup.exceptions import MaterialsInsufficientError, SubjectDuplicateError
from aperix_geo.services.setup.finalize import finalize_setup
from aperix_geo.services.setup.materials_store import (
    add_setup_upload_file,
    delete_setup_upload_file,
    ensure_brand_setup_session,
    save_setup_materials,
)
from aperix_geo.services.setup.topics import run_setup_topics_step

router = APIRouter(prefix="/setup", tags=["setup"])


@router.post("/session", response_model=SetupSessionCreateResponse)
def create_setup_session_endpoint(
    body: SetupSessionCreateRequest,
    db: DbSession,
    current: CurrentUser,
) -> SetupSessionCreateResponse:
    try:
        session_id = ensure_brand_setup_session(
            db=db,
            tenant_id=current.tenant_id,
            user_id=str(current.id),
            brand=body.brand.strip(),
            region=body.region,
            language=body.language,
            session_id=body.session_id,
        )
    except SubjectDuplicateError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": e.code, "message": e.message},
        ) from e
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    return SetupSessionCreateResponse(session_id=session_id)


@router.put("/materials", response_model=SetupMaterialsSaveResponse)
def save_setup_materials_endpoint(
    body: SetupMaterialsSaveRequest,
    current: CurrentUser,
) -> SetupMaterialsSaveResponse:
    save_setup_materials(
        user_id=str(current.id),
        session_id=body.session_id.strip(),
        brand_intro=body.brand_intro,
        website_url=body.website_url,
    )
    return SetupMaterialsSaveResponse(session_id=body.session_id.strip(), materials_saved=True)


@router.post("/materials/files", response_model=SetupUploadFileOut)
def upload_setup_material_file_endpoint(
    current: CurrentUser,
    session_id: str = Form(...),
    file: UploadFile = File(...),
) -> SetupUploadFileOut:
    entry = add_setup_upload_file(
        user_id=str(current.id),
        session_id=session_id.strip(),
        upload=file,
    )
    return SetupUploadFileOut(
        id=str(entry["id"]),
        name=str(entry["name"]),
        mime=str(entry["mime"]),
        size=int(entry["size"]),
        status=str(entry.get("status") or "ok"),
    )


@router.delete("/materials/files/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_setup_material_file_endpoint(
    file_id: str,
    session_id: str,
    current: CurrentUser,
) -> None:
    delete_setup_upload_file(
        user_id=str(current.id),
        session_id=session_id.strip(),
        file_id=file_id.strip(),
    )


@router.post("/discover", response_model=SetupDiscoverResponse)
def discover_setup_endpoint(
    body: SetupDiscoverRequest,
    db: DbSession,
    current: CurrentUser,
) -> SetupDiscoverResponse:
    try:
        result = discover_setup(
            db=db,
            tenant_id=current.tenant_id,
            user_id=current.id,
            session_id=body.session_id,
            subject_type=body.type.value,
            domain=body.domain.strip() if body.domain else None,
            brand=body.brand.strip() if body.brand else None,
            region=body.region,
            language=body.language,
        )
    except QuotaExceededError as e:
        raise quota_exceeded_http_exception(e) from e
    except MaterialsInsufficientError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": e.code, "message": e.message},
        ) from e
    except SubjectDuplicateError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": e.code, "message": e.message},
        ) from e
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
    db: DbSession,
    current: CurrentUser,
) -> SetupTopicsResponse:
    try:
        topics = run_setup_topics_step(
            db=db,
            tenant_id=current.tenant_id,
            user_id=str(current.id),
            session_id=body.session_id.strip(),
            competitors=body.competitors,
        )
    except QuotaExceededError as e:
        raise quota_exceeded_http_exception(e) from e
    except ValueError as e:
        status_code = status.HTTP_404_NOT_FOUND if "not found" in str(e) else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=status_code, detail=str(e)) from e
    except (LLMProviderError, json.JSONDecodeError, TypeError) as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"监测主题生成失败：{e}",
        ) from e
    return SetupTopicsResponse(
        topics=[SetupMonitoringTopicOut(**item) for item in topics],
    )


@router.post("/prompts", response_model=SetupPromptsGenerateResponse)
def generate_setup_prompts_endpoint(
    body: SetupPromptsGenerateRequest,
    db: DbSession,
    current: CurrentUser,
) -> SetupPromptsGenerateResponse:
    try:
        items = generate_setup_prompts_for_session(
            db=db,
            tenant_id=current.tenant_id,
            user_id=str(current.id),
            session_id=body.session_id.strip(),
            topics=body.topics,
            exclude_prompts=body.exclude_prompts,
        )
    except QuotaExceededError as e:
        raise quota_exceeded_http_exception(e) from e
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
    subject, job, knowledge_ready = finalize_setup(
        db,
        user=current,
        session_id=body.session_id.strip(),
        body=body,
    )
    db.commit()
    if knowledge_ready:
        from aperix_geo.services.knowledge.persist import enqueue_knowledge_index

        enqueue_knowledge_index(subject.id)
    return SetupFinalizeResponse(subject_id=subject.id, sampling_job_id=job.id)
