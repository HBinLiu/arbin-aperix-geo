"""品牌 Setup 资料保存与文件上传（会话期）。"""

from __future__ import annotations

import re
import uuid
from pathlib import Path
from typing import Any
from uuid import UUID

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from aperix_geo.config import Settings, get_settings
from aperix_geo.services.setup.cache import create_session, get_session, update_session
from aperix_geo.services.setup.upload import extract_upload_text, upload_suffix
from aperix_geo.schemas.url_fields import validate_optional_http_url

MAX_UPLOAD_FILES = 10
MAX_UPLOAD_BYTES = 5 * 1024 * 1024


def _has_any_material(*, intro: str, url: str, upload_files: list[Any]) -> bool:
    if url.strip():
        return True
    if intro.strip():
        return True
    return len(upload_files) > 0


def _upload_root(settings: Settings | None = None) -> Path:
    cfg = settings or get_settings()
    root = Path(cfg.setup_upload_dir).expanduser()
    root.mkdir(parents=True, exist_ok=True)
    return root


def _safe_filename(name: str) -> str:
    base = Path(name).name.strip()
    cleaned = re.sub(r"[^\w.\-()\u4e00-\u9fff]+", "_", base)
    return cleaned[:200] or "upload.bin"


def _brand_session_payload(*, brand: str, region: str, language: str) -> dict[str, Any]:
    target = brand.strip()
    return {
        "subject_type": "brand",
        "target": target,
        "brand": target,
        "domain": None,
        "website_url": "",
        "region": region.strip() or "CN",
        "language": language.strip() or "zh-CN",
        "brand_intro": "",
        "upload_files": [],
        "materials_saved": False,
        "profile_hash": "",
        "profile": {},
        "monitoring_topics": [],
        "research_payload": {},
        "profile_summary": "",
        "competitors": [],
    }


def ensure_brand_setup_session(
    *,
    db: Session,
    tenant_id: UUID,
    user_id: str,
    brand: str,
    region: str,
    language: str,
    session_id: str | None = None,
) -> str:
    target = brand.strip()
    if not target:
        raise ValueError("brand is required")

    from aperix_geo.services.subject.duplicate import assert_tenant_subject_unique

    assert_tenant_subject_unique(
        db,
        tenant_id=tenant_id,
        subject_type="brand",
        brand=target,
    )

    sid = (session_id or "").strip()
    if sid:
        existing = get_session(user_id=user_id, session_id=sid)
        if existing and existing.get("subject_type") == "brand":
            update_session(
                user_id=user_id,
                session_id=sid,
                patch={
                    "target": target,
                    "brand": target,
                    "region": region.strip() or "CN",
                    "language": language.strip() or "zh-CN",
                },
            )
            return sid

    return create_session(
        user_id=user_id,
        payload=_brand_session_payload(brand=target, region=region, language=language),
    )


def save_setup_materials(
    *,
    user_id: str,
    session_id: str,
    brand_intro: str,
    website_url: str = "",
) -> dict[str, Any]:
    sid = session_id.strip()
    session = get_session(user_id=user_id, session_id=sid)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="setup session not found")
    if session.get("subject_type") != "brand":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="materials only for brand setup")

    intro = brand_intro.strip()
    upload_files = list(session.get("upload_files") or [])
    raw_url = website_url.strip()
    url = ""
    if raw_url:
        try:
            url = validate_optional_http_url(raw_url)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="请填写有效的品牌 URL",
            ) from exc
    if not _has_any_material(intro=intro, url=url, upload_files=upload_files):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="请至少填写品牌 URL、品牌介绍或上传文件其中一项",
        )

    patch: dict[str, Any] = {
        "brand_intro": intro,
        "website_url": url,
        "materials_saved": True,
    }
    if not update_session(user_id=user_id, session_id=sid, patch=patch):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="setup session not found")
    return get_session(user_id=user_id, session_id=sid) or {}


def add_setup_upload_file(
    *,
    user_id: str,
    session_id: str,
    upload: UploadFile,
) -> dict[str, Any]:
    sid = session_id.strip()
    session = get_session(user_id=user_id, session_id=sid)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="setup session not found")
    if session.get("subject_type") != "brand":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="upload only for brand setup")

    files = list(session.get("upload_files") or [])
    if len(files) >= MAX_UPLOAD_FILES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"最多上传 {MAX_UPLOAD_FILES} 个文件")

    filename = _safe_filename(upload.filename or "upload.txt")
    suffix = upload_suffix(filename)
    if not suffix:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="仅支持 .docx、.md、.txt")

    raw = upload.file.read()
    if len(raw) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="单文件不能超过 5MB")

    try:
        extracted = extract_upload_text(filename=filename, content=raw)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    file_id = uuid.uuid4().hex
    rel_key = f"{user_id}/{sid}/{file_id}_{filename}"
    dest = _upload_root() / rel_key
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(raw)

    mime = (upload.content_type or "").strip() or "application/octet-stream"
    entry = {
        "id": file_id,
        "name": filename,
        "mime": mime,
        "size": len(raw),
        "storage_key": rel_key,
        "extracted_text": extracted,
        "status": "ok",
    }
    files.append(entry)
    if not update_session(user_id=user_id, session_id=sid, patch={"upload_files": files, "materials_saved": False}):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="setup session not found")
    return entry


def delete_setup_upload_file(*, user_id: str, session_id: str, file_id: str) -> None:
    sid = session_id.strip()
    fid = file_id.strip()
    session = get_session(user_id=user_id, session_id=sid)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="setup session not found")

    files = list(session.get("upload_files") or [])
    kept: list[dict[str, Any]] = []
    removed: dict[str, Any] | None = None
    for item in files:
        if str(item.get("id") or "") == fid:
            removed = item
        else:
            kept.append(item)
    if removed is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="upload file not found")

    storage_key = str(removed.get("storage_key") or "").strip()
    if storage_key:
        path = _upload_root() / storage_key
        if path.is_file():
            path.unlink(missing_ok=True)

    update_session(
        user_id=user_id,
        session_id=sid,
        patch={"upload_files": kept, "materials_saved": False},
    )
