"""Knowledge base API schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class SubjectKnowledgeOut(BaseModel):
    id: UUID
    subject_id: UUID
    status: str
    version: int
    index_status: str
    indexed_version: int
    index_error: str
    verified_at: datetime
    updated_at: datetime


class KnowledgeSourceOut(BaseModel):
    id: UUID
    kind: str
    title: str
    uri: str
    mime_type: str
    file_size: int
    char_count: int
    parse_status: str
    parse_error: str
    sort_order: int
    raw_text_preview: str
    raw_text: str = ""
    created_at: datetime
    updated_at: datetime


class KnowledgeTextSourceBody(BaseModel):
    text: str
    title: str = "品牌介绍"


class KnowledgeSourceUpdateBody(BaseModel):
    text: str
    title: str | None = None


class SubjectKnowledgeDetailOut(BaseModel):
    knowledge: SubjectKnowledgeOut | None
    sources: list[KnowledgeSourceOut] = Field(default_factory=list)
    chunk_count: int = 0
