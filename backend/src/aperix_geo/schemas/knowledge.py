"""Knowledge base API schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SubjectKnowledgeOut(BaseModel):
    id: UUID
    subject_id: UUID
    status: str
    version: int
    index_status: str
    indexed_version: int
    index_error: str
    extract_status: str = "pending"
    extract_error: str = ""
    node_count: int = 0
    edge_count: int = 0
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


class KnowledgeGraphNodeOut(BaseModel):
    id: str
    type: str
    label: str
    aliases: list[str] = Field(default_factory=list)
    source_ids: list[str] = Field(default_factory=list)
    confidence: float = 0.0


class KnowledgeGraphEdgeOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True, ser_json_by_alias=True)

    id: str
    type: str
    from_id: str = Field(validation_alias="from", serialization_alias="from")
    to_id: str = Field(validation_alias="to", serialization_alias="to")
    label: str = ""
    source_ids: list[str] = Field(default_factory=list)
    evidence: str = ""
    confidence: float = 0.0


class KnowledgeGraphOut(BaseModel):
    schema_version: int = 1
    extract_status: str
    extract_error: str = ""
    extracted_at: str = ""
    nodes: list[KnowledgeGraphNodeOut] = Field(default_factory=list)
    edges: list[KnowledgeGraphEdgeOut] = Field(default_factory=list)


class SubjectKnowledgeDetailOut(BaseModel):
    knowledge: SubjectKnowledgeOut | None
    sources: list[KnowledgeSourceOut] = Field(default_factory=list)
    chunk_count: int = 0
    graph: KnowledgeGraphOut | None = None
