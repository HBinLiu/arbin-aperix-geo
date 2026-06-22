"""Diagnosis center query parameters (no FilterBar window / platform / topic)."""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from aperix_geo.api.schemas.analysis_query import ContentOpportunitySortField


class DiagnosisContentParams(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=10, ge=1, le=100)
    sort_by: ContentOpportunitySortField | None = None
    order: Literal["asc", "desc"] = "asc"


class DiagnosisContentDetailParams(BaseModel):
    prompt_id: UUID
