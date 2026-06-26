"""Subject / topic / prompt schemas."""

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from aperix_geo.schemas.url_fields import validate_optional_http_url


class SubjectTypeEnum(str, Enum):
    domain = "domain"
    brand = "brand"


class SubjectUpdate(BaseModel):
    brand: str | None = None
    aliases: list[str] | None = None
    profile_summary: str | None = None
    sampling_platforms: list[str] | None = None


class SubjectOut(BaseModel):
    id: UUID
    tenant_id: UUID
    type: str
    domain: str
    brand: str
    website_url: str
    aliases: list[str]
    summary: str
    profile_summary: str
    sampling_platforms: list[str]
    last_sampled_at: datetime
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CompetitorItem(BaseModel):
    domain: str = Field(default="", max_length=255)
    website_url: str = Field(default="", max_length=255)
    brand: str = Field(default="", max_length=255)
    aliases: list[str] = Field(default_factory=list)
    summary: str = Field(default="")
    cross_validate_score: float | None = None
    cross_validate_reason: str = Field(default="")

    @field_validator("website_url", mode="before")
    @classmethod
    def _validate_website_url(cls, v: object) -> str:
        return validate_optional_http_url(v)


class ConfiguredCompetitorItem(CompetitorItem):
    id: UUID


class CompetitorsUpdate(BaseModel):
    competitors: list[CompetitorItem] = Field(default_factory=list)


class CompetitorsOut(BaseModel):
    competitors: list[ConfiguredCompetitorItem] = Field(default_factory=list)


class PromoteBrandOut(BaseModel):
    competitor: ConfiguredCompetitorItem
    brand_id: UUID
    entity_label: str
    signals_migrated: int
    signals_dropped: int


class DiscoveredCompetitor(BaseModel):
    domain: str = Field(default="", description="主域名（eTLD+1）；品牌模式竞品为空")
    website_url: str = Field(default="", description="官网 URL")
    brand: str = Field(..., description="公司/品牌名称")
    summary: str = Field(default="", description="站点 meta description 摘要")
    aliases: list[str] = Field(default_factory=list, description="品牌别名/常用简称")

    @field_validator("website_url", mode="before")
    @classmethod
    def _validate_website_url(cls, v: object) -> str:
        return validate_optional_http_url(v)


class SetupDiscoverCompetitorOut(BaseModel):
    """discover 响应：仅 Step1 UI 展示所需字段；summary/aliases 在 session.competitors。"""

    domain: str = Field(default="", max_length=255)
    website_url: str = Field(default="", max_length=255)
    brand: str = Field(..., max_length=255)

    @field_validator("website_url", mode="before")
    @classmethod
    def _validate_website_url(cls, v: object) -> str:
        return validate_optional_http_url(v)


class GeneratedPromptOut(BaseModel):
    text: str
    funnel_stage: str
    search_intent: str


class TopicPromptsOut(BaseModel):
    topic: str
    prompts: list[GeneratedPromptOut]


class SetupPromptItem(BaseModel):
    text: str = Field(..., min_length=1)
    funnel_stage: str = Field(default="mofu", max_length=8)
    search_intent: str = Field(default="commercial", max_length=16)


class SetupTopicItem(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    prompts: list[SetupPromptItem] = Field(default_factory=list)


class SetupDiscoverRequest(BaseModel):
    type: SubjectTypeEnum
    domain: str | None = None
    brand: str | None = None
    region: str = Field(default="CN", max_length=32)
    language: str = Field(default="zh-CN", max_length=16)
    session_id: str | None = Field(
        default=None,
        description="退回后重试时携带，用于 session / 竞品缓存命中",
    )


class SetupDiscoverResponse(BaseModel):
    session_id: str = Field(..., description="Redis 会话 ID，后续步骤须携带")
    competitors: list[SetupDiscoverCompetitorOut] = Field(default_factory=list)


class SetupCompetitorsResponse(BaseModel):
    competitors: list[DiscoveredCompetitor] = Field(default_factory=list)


class SetupPromptsGenerateRequest(BaseModel):
    session_id: str = Field(..., min_length=1)
    topics: list[str] = Field(..., min_length=1, description="用户确认后的监测主题")
    exclude_prompts: list[str] = Field(default_factory=list)


class SetupPromptsGenerateResponse(BaseModel):
    items: list[TopicPromptsOut] = Field(default_factory=list)


class SetupTopicsRequest(BaseModel):
    session_id: str = Field(..., min_length=1)
    competitors: list[CompetitorItem] = Field(
        ...,
        min_length=1,
        description="用户在 Step1 确认后的竞品列表",
    )


class SetupTopicsResponse(BaseModel):
    monitoring_topics: list[str] = Field(default_factory=list)


class SetupFinalizeBody(BaseModel):
    session_id: str = Field(..., min_length=1)
    topics: list[SetupTopicItem] = Field(..., min_length=1)


class SetupFinalizeResponse(BaseModel):
    subject_id: UUID
    sampling_job_id: UUID


class GenerateSubjectPromptsRequest(BaseModel):
    topic_id: UUID
    count: int = Field(..., ge=1, le=50)


class TopicCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)


class TopicOut(BaseModel):
    id: UUID
    subject_id: UUID
    name: str
    created_at: datetime

    model_config = {"from_attributes": True}


class PromptCreate(BaseModel):
    topic_id: UUID
    text: str = Field(..., min_length=1)
    funnel_stage: str = Field(default="mofu", max_length=8)
    search_intent: str = Field(default="commercial", max_length=16)
    enabled: bool = True


class PromptBatchItem(BaseModel):
    text: str = Field(..., min_length=1)
    funnel_stage: str = Field(default="mofu", max_length=8)
    search_intent: str = Field(default="commercial", max_length=16)


class PromptBatchCreate(BaseModel):
    topic_id: UUID
    items: list[PromptBatchItem] = Field(..., min_length=1, max_length=50)


class PromptUpdate(BaseModel):
    topic_id: UUID | None = None
    text: str | None = None
    funnel_stage: str | None = Field(default=None, max_length=8)
    search_intent: str | None = Field(default=None, max_length=16)
    enabled: bool | None = None


class PromptOut(BaseModel):
    id: UUID
    subject_id: UUID
    topic_id: UUID
    text: str
    funnel_stage: str
    search_intent: str
    enabled: bool
    created_at: datetime

    model_config = {"from_attributes": True}
