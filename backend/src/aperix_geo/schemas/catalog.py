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
    note: str | None = Field(default=None, description="旧版自由文本备忘（迁移遗留）")


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


class CompetitorDomainItem(BaseModel):
    domain: str = Field(..., min_length=1, max_length=255)
    website_url: str = Field(default="", max_length=255)
    site_name: str = Field(default="", max_length=255)


class CompetitorsUpdate(BaseModel):
    competitors: list[CompetitorDomainItem] = Field(default_factory=list)
    brand_names: list[str] = Field(default_factory=list)
    # 兼容旧客户端：仅传 domains 时 site_name 为空字符串
    domains: list[str] = Field(default_factory=list)


class CompetitorsOut(BaseModel):
    competitors: list[CompetitorDomainItem] = Field(default_factory=list)
    domains: list[str] = Field(default_factory=list)
    brand_names: list[str] = Field(default_factory=list)


class DiscoverProfileRequest(BaseModel):
    type: SubjectTypeEnum
    domain: str | None = None
    brand: str | None = None
    region: str = Field(default="CN", max_length=32)
    language: str = Field(default="zh-CN", max_length=16)


class DiscoverProfileResponse(BaseModel):
    session_id: str = Field(..., description="Redis 会话 ID，后续步骤须携带")
    micro_keywords: list[str] = Field(default_factory=list)


class DiscoverCompetitorsSearchRequest(BaseModel):
    session_id: str = Field(..., min_length=8, max_length=64)
    micro_keywords: list[str] | None = Field(
        default=None,
        description="用户确认后的主题/检索词；不传则使用会话内缓存",
    )


class DiscoveredCompetitor(BaseModel):
    domain: str = Field(..., description="主域名（eTLD+1）")
    site_name: str = Field(..., description="中文站点名称（来自页面 title）")


class DiscoverCompetitorsResponse(BaseModel):
    session_id: str | None = Field(default=None, description="关联的设置向导 Redis 会话")
    domains: list[str] = Field(default_factory=list)
    competitors: list[DiscoveredCompetitor] = Field(default_factory=list)
    brand_names: list[str] = Field(default_factory=list)
    micro_keywords: list[str] = Field(
        default_factory=list,
        description="确认后的微观利基检索词",
    )


class GeneratePromptsRequest(BaseModel):
    session_id: str = Field(..., min_length=8, max_length=64)
    topics: list[str] = Field(..., min_length=1)
    competitors: list[str] = Field(default_factory=list)


class TopicPromptsOut(BaseModel):
    topic: str
    prompts: list[str]


class GeneratePromptsResponse(BaseModel):
    items: list[TopicPromptsOut]


class SetupTopicItem(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    prompts: list[str] = Field(default_factory=list)


class SetupFinalizeRequest(BaseModel):
    type: SubjectTypeEnum
    domain: str | None = None
    brand: str | None = None
    monitoring_scope: MonitoringScope | None = None
    setup_session_id: str | None = Field(
        default=None,
        min_length=8,
        max_length=64,
        description="设置向导 Redis 会话 ID，用于读取 profile_summary",
    )
    competitors: list[CompetitorDomainItem] = Field(default_factory=list)
    brand_names: list[str] = Field(default_factory=list)
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
    enabled: bool = True


class PromptUpdate(BaseModel):
    topic_id: UUID | None = None
    text: str | None = None
    enabled: bool | None = None


class PromptOut(BaseModel):
    id: UUID
    subject_id: UUID
    topic_id: UUID
    text: str
    enabled: bool
    created_at: datetime

    model_config = {"from_attributes": True}
