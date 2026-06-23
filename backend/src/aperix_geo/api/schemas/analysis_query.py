"""Shared analysis query parameter models (field order = OpenAPI / query string order)."""

from __future__ import annotations

from uuid import UUID

from typing import Literal

from pydantic import BaseModel, Field

MatrixRowDimension = Literal["competitor", "topic"]


class AnalysisWindowParams(BaseModel):
    """subjectId 之后：entity → platform → topic → prompt → search → start_date/end_date。"""

    entity_id: str | None = None
    platform: list[str] | None = None
    topic_id: list[UUID] | None = None
    prompt_id: UUID | None = None
    search: str | None = None
    start_date: str
    end_date: str


class AnalysisRankWindowParams(BaseModel):
    platform: list[str] | None = None
    topic_id: list[UUID] | None = None
    start_date: str
    end_date: str


class AnalysisPromptSortParams(AnalysisWindowParams):
    sort_by: str | None = None
    order: str = "desc"


PromptPerformanceSortField = Literal[
    "visibility_rate",
    "mention_rate",
    "average_rank",
    "citation_rate",
    "sentiment_score",
]


class AnalysisPromptsParams(AnalysisWindowParams):
    sort_by: PromptPerformanceSortField | None = None
    order: Literal["asc", "desc"] = "desc"
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=10, ge=1, le=100)


class PlatformAnalysisParams(AnalysisWindowParams):
    matrix_row: MatrixRowDimension = "competitor"


SentimentTab = Literal["positive", "neutral", "negative"]


AnalysisResponseSortField = Literal["created_at", "sentiment_score", "rank"]


class AnalysisResponsesParams(AnalysisWindowParams):
    sentiment_label: SentimentTab | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=10, ge=1, le=100)
    sort_by: AnalysisResponseSortField | None = None
    order: Literal["asc", "desc"] = "desc"


class CitationDomainAnalysisParams(AnalysisWindowParams):
    domain: str


CitationDomainPromptSortField = Literal["count", "citation_rate"]


class CitationDomainUrlsParams(CitationDomainAnalysisParams):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=10, ge=1, le=100)
    sort_by: Literal["count", "citation_rate"] = "count"
    order: Literal["asc", "desc"] = "desc"


class CitationDomainPromptsParams(CitationDomainAnalysisParams):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=10, ge=1, le=100)
    sort_by: CitationDomainPromptSortField = "count"
    order: Literal["asc", "desc"] = "desc"


class CitationDomainsParams(AnalysisWindowParams):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=10, ge=1, le=100)
    sort_by: Literal["count"] = "count"
    order: Literal["asc", "desc"] = "desc"


class CitationUrlsParams(AnalysisWindowParams):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=10, ge=1, le=100)
    sort_by: Literal["count", "citation_rate"] = "count"
    order: Literal["asc", "desc"] = "desc"


ContentOpportunitySortField = Literal[
    "priority",
    "brand_gap_rate",
    "source_gap_rate",
    "mention_rate",
]


BacklinkOpportunitySortField = Literal["priority", "prompt_count", "chat_count", "citation_count"]


class OpportunityWindowParams(BaseModel):
    """机会页接口：始终以自有品牌为焦点，不接受 entity_id。"""

    platform: list[str] | None = None
    topic_id: list[UUID] | None = None
    prompt_id: UUID | None = None
    search: str | None = None
    start_date: str
    end_date: str


class BacklinkOpportunityParams(OpportunityWindowParams):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=10, ge=1, le=100)
    search: str | None = None
    sort_by: BacklinkOpportunitySortField | None = None
    order: Literal["asc", "desc"] = "asc"


class BacklinkOpportunityDetailParams(OpportunityWindowParams):
    domain: str


class BacklinkOpportunityUrlsParams(BacklinkOpportunityDetailParams):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=10, ge=1, le=100)
    sort_by: Literal["count", "citation_rate"] = "count"
    order: Literal["asc", "desc"] = "desc"


class BacklinkOpportunityPromptsParams(BacklinkOpportunityDetailParams):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=10, ge=1, le=100)
    sort_by: Literal["count", "citation_rate"] = "count"
    order: Literal["asc", "desc"] = "desc"
