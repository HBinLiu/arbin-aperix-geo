"""Sampling job / response schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from aperix_geo.db.models import SamplingJobStatus

class SamplingJobCreate(BaseModel):
    prompt_ids: list[UUID] | None = None
    platforms: list[str] | None = Field(
        default=None,
        description="采样平台列表（如 doubao）；不传则使用主体配置或默认平台",
    )


class SamplingPlatformOut(BaseModel):
    platform: str
    label: str


class SamplingJobOut(BaseModel):
    id: UUID
    tenant_id: UUID
    subject_id: UUID
    status: SamplingJobStatus
    total_items: int
    completed_items: int
    failed_items: int
    error_message: str
    created_at: datetime
    started_at: datetime
    finished_at: datetime

    model_config = ConfigDict(from_attributes=True, use_enum_values=True)


class SampleSyncRequest(BaseModel):
    prompt_id: UUID
    platform: str | None = Field(default=None, description="指定平台；默认取首个已配置平台")
    persist: bool = False
