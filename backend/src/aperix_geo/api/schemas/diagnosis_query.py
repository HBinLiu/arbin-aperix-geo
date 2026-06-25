"""Diagnosis center query parameters (FilterBar window / platform / topic)."""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from aperix_geo.api.schemas.analysis_query import ContentOpportunitySortField, OpportunityWindowParams


class DiagnosisContentParams(OpportunityWindowParams):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=10, ge=1, le=100)
    sort_by: ContentOpportunitySortField | None = None
    order: Literal["asc", "desc"] = "asc"


class DiagnosisContentSummaryParams(OpportunityWindowParams):
    pass


class DiagnosisContentDetailParams(OpportunityWindowParams):
    prompt_id: UUID
