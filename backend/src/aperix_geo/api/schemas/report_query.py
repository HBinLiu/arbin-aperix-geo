"""Brand report request parameters."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel


class BrandReportParams(BaseModel):
    start_date: str
    end_date: str
    entity_id: str | None = None
    platform: list[str] | None = None
    topic_id: list[UUID] | None = None
