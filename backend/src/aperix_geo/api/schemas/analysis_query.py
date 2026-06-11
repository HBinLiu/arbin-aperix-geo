"""Shared analysis query parameter models (field order = OpenAPI / query string order)."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AnalysisWindowParams(BaseModel):
    """subjectId 之后：entity → platform → topic → prompt → from/to。"""

    model_config = ConfigDict(populate_by_name=True)

    entity_id: str | None = None
    platform: list[str] | None = None
    topic_id: UUID | None = None
    prompt_id: UUID | None = None
    from_: str = Field(alias="from")
    to: str


class AnalysisRankWindowParams(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    platform: list[str] | None = None
    topic_id: UUID | None = None
    from_: str = Field(alias="from")
    to: str


class AnalysisPromptSortParams(AnalysisWindowParams):
    sort_by: str | None = None
    order: str = "desc"


class AnalysisMetricsParams(AnalysisWindowParams):
    group_by: str = "none"
    sort_by: str | None = None
    order: str = "desc"


class CitationDomainParams(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    entity_id: str | None = None
    platform: list[str] | None = None
    topic_id: UUID | None = None
    prompt_id: UUID | None = None
    host: str
    from_: str = Field(alias="from")
    to: str
