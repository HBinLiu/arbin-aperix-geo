"""Finalize 时将品牌 Setup session 资料写入知识库表。"""

from __future__ import annotations

import logging
import shutil
import uuid
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from aperix_geo.config import get_settings
from aperix_geo.db.base import utc_now
from aperix_geo.db.models import KnowledgeSource, Subject, SubjectKnowledge
from aperix_geo.services.setup.materials_store import _upload_root

logger = logging.getLogger(__name__)


def persist_brand_knowledge_from_setup(
    db: Session,
    *,
    subject: Subject,
    setup_session: dict[str, Any],
    user_id: UUID,
) -> SubjectKnowledge | None:
    if not setup_session.get("materials_saved"):
        return None
    intro = str(setup_session.get("brand_intro") or "").strip()
    if not intro:
        return None

    brand = str(setup_session.get("brand") or subject.brand or "").strip()
    website_url = str(setup_session.get("website_url") or subject.website_url or "").strip()
    profile = dict(setup_session.get("profile") or {})

    knowledge = SubjectKnowledge(
        tenant_id=subject.tenant_id,
        subject_id=subject.id,
        status="verified",
        version=1,
        index_status="pending",
        indexed_version=0,
        index_error="",
        identity_json={
            "primary_name": brand,
            "aliases": list(subject.aliases or []),
            "negative_aliases": [],
            "category": "",
            "disambiguation": "",
            "official_url": website_url,
        },
        facts_json={
            "industry": str(profile.get("industry") or "").strip(),
            "icp": str(profile.get("customers") or "").strip(),
            "products": [p for p in str(profile.get("features") or "").split("、") if p.strip()],
            "pain_points": [],
            "differentiators": [],
        },
        relations_json={},
        narrative_json={
            "overview": intro[:4000],
        },
        voice_json={},
        verified_at=utc_now(),
        verified_by_user_id=user_id,
    )
    db.add(knowledge)
    db.flush()

    sort_order = 0
    db.add(
        _source_row(
            tenant_id=subject.tenant_id,
            subject_id=subject.id,
            kind="user_input",
            title="品牌介绍",
            uri="",
            raw_text=intro,
            sort_order=sort_order,
        )
    )
    sort_order += 1

    for item in setup_session.get("upload_files") or []:
        if not isinstance(item, dict):
            continue
        text = str(item.get("extracted_text") or "").strip()
        if not text:
            continue
        storage_key = _finalize_storage_key(item)
        db.add(
            _source_row(
                tenant_id=subject.tenant_id,
                subject_id=subject.id,
                kind="upload",
                title=str(item.get("name") or "upload"),
                uri="",
                raw_text=text,
                mime_type=str(item.get("mime") or ""),
                file_size=int(item.get("size") or 0),
                storage_key=storage_key,
                sort_order=sort_order,
                metadata_json={"upload_file_id": str(item.get("id") or "")},
            )
        )
        sort_order += 1

    research = setup_session.get("research_payload") or {}
    homepage = research.get("homepage") if isinstance(research, dict) else {}
    if isinstance(homepage, dict):
        homepage_text = str(homepage.get("text") or "").strip()
        homepage_url = str(homepage.get("url") or website_url).strip()
        if homepage_text:
            db.add(
                _source_row(
                    tenant_id=subject.tenant_id,
                    subject_id=subject.id,
                    kind="homepage",
                    title=homepage_url or "homepage",
                    uri=homepage_url,
                    raw_text=homepage_text,
                    sort_order=sort_order,
                )
            )

    return knowledge


def enqueue_knowledge_index(subject_id: UUID) -> None:
    try:
        from aperix_geo.tasks.knowledge import index_subject

        index_subject.delay(str(subject_id))
    except Exception:
        logger.warning("knowledge index enqueue failed subject=%s", subject_id, exc_info=True)


def _source_row(
    *,
    tenant_id: UUID,
    subject_id: UUID,
    kind: str,
    title: str,
    uri: str,
    raw_text: str,
    sort_order: int,
    mime_type: str = "",
    file_size: int = 0,
    storage_key: str = "",
    metadata_json: dict[str, Any] | None = None,
) -> KnowledgeSource:
    return KnowledgeSource(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        subject_id=subject_id,
        kind=kind,
        title=title[:255],
        uri=uri[:2048],
        mime_type=mime_type,
        file_size=file_size,
        storage_key=storage_key,
        raw_text=raw_text,
        char_count=len(raw_text),
        parse_status="ok",
        parse_error="",
        metadata_json=metadata_json or {},
        sort_order=sort_order,
    )


def _finalize_storage_key(item: dict[str, Any]) -> str:
    session_key = str(item.get("storage_key") or "").strip()
    if not session_key:
        return ""
    src = _upload_root() / session_key
    if not src.is_file():
        return session_key
    settings = get_settings()
    root = Path(settings.knowledge_upload_dir).expanduser()
    root.mkdir(parents=True, exist_ok=True)
    dest_key = f"knowledge/{session_key}"
    dest = root / dest_key
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)
    return dest_key
