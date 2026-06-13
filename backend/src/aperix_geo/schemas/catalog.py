"""Subject / topic / prompt schemas."""

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field


class SubjectTypeEnum(str, Enum):
    domain = "domain"
    brand = "brand"


class MonitoringScope(BaseModel):
    region: str = Field(default="CN", max_length=32)
    language: str = Field(default="zh-CN", max_length=16)
    note: str | None = Field(default=None, description="监测范围备注")


class SubjectCreate(BaseModel):
    type: SubjectTypeEnum
    domain: str | None = None
    brand: str | None = None
    website_url: str | None = None
    aliases: list[str] = Field(default_factory=list)
    monitoring_scope: MonitoringScope | None = None


class SubjectUpdate(BaseModel):
    domain: str | None = None
    brand: str | None = None
    website_url: str | None = None
    aliases: list[str] | None = None
    monitoring_scope: MonitoringScope | None = None
    profile_summary: str | None = None
    sampling_platforms: list[str] | None = None
    sampling_interval: int | None = Field(
        default=None,
        description="定时采样间隔（小时）；0 表示关闭；允许 0,6,12,24,72,168",
    )


class SubjectOut(BaseModel):
    id: UUID
    tenant_id: UUID
    type: str
    domain: str
    brand: str
    website_url: str
    aliases: list[str]
    monitoring_scope: MonitoringScope
    profile_summary: str
    sampling_platforms: list[str]
    sampling_interval: int
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


class CompetitorsUpdate(BaseModel):
    competitors: list[CompetitorItem] = Field(default_factory=list)


class CompetitorsOut(BaseModel):
    competitors: list[CompetitorItem] = Field(default_factory=list)


class DiscoverProfileRequest(BaseModel):
    type: SubjectTypeEnum
    domain: str | None = None
    brand: str | None = None
    region: str = Field(default="CN", max_length=32)
    language: str = Field(default="zh-CN", max_length=16)


class DiscoverProfileResponse(BaseModel):
    session_id: str = Field(..., description="Redis 会话 ID，后续步骤须携带")
    monitoring_topics: list[str] = Field(default_factory=list, description="监测主题（用于生成提示词）")


class DiscoverCompetitorsSearchRequest(BaseModel):
    session_id: str = Field(..., min_length=8, max_length=64)
    monitoring_topics: list[str] = Field(..., min_length=1, description="用户确认后的监测主题")


class DiscoveredCompetitor(BaseModel):
    domain: str = Field(default="", description="主域名（eTLD+1）；品牌模式竞品为空")
    website_url: str = Field(default="", description="官网 URL")
    brand: str = Field(..., description="公司/品牌名称（竞品分析阶段总结）")
    summary: str = Field(default="", description="竞品介绍（竞品分析阶段总结，含定位与竞争关系）")


class DiscoverCompetitorsResponse(BaseModel):
    competitors: list[DiscoveredCompetitor] = Field(default_factory=list)


class GeneratePromptsRequest(BaseModel):
    session_id: str = Field(..., min_length=8, max_length=64)
    topics: list[str] = Field(..., min_length=1)
    competitors: list[str] = Field(default_factory=list)
    exclude_prompts: list[str] = Field(default_factory=list)


class GeneratedPromptOut(BaseModel):
    text: str
    funnel_stage: str
    search_intent: str


class TopicPromptsOut(BaseModel):
    topic: str
    prompts: list[GeneratedPromptOut]


class GeneratePromptsResponse(BaseModel):
    items: list[TopicPromptsOut]


class GenerateSubjectPromptsRequest(BaseModel):
    topic_id: UUID
    count: int = Field(..., ge=1, le=20)


class SetupPromptItem(BaseModel):
    text: str = Field(..., min_length=1)
    funnel_stage: str = Field(default="mofu", max_length=8)
    search_intent: str = Field(default="commercial", max_length=16)


class SetupTopicItem(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    prompts: list[SetupPromptItem] = Field(default_factory=list)


class SetupFinalizeRequest(BaseModel):
    setup_session_id: str = Field(
        ...,
        min_length=8,
        max_length=64,
        description="设置向导 Redis 会话 ID（主体类型、监测范围、profile_summary 等从会话读取）",
    )
    competitors: list[CompetitorItem] = Field(default_factory=list)
    topics: list[SetupTopicItem] = Field(..., min_length=1)


class SetupFinalizeResponse(BaseModel):
    subject: SubjectOut
    sampling_job_id: UUID


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
