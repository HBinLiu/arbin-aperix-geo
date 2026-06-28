"""In-app notification API schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class NotificationOut(BaseModel):
    id: UUID
    category: str
    title: str
    body: str
    action_url: str
    read: bool
    created_at: datetime


class NotificationListOut(BaseModel):
    items: list[NotificationOut]
    unread_count: int


class UnreadCountOut(BaseModel):
    unread_count: int


class MarkReadOut(BaseModel):
    ok: bool = True
    id: UUID
    read: bool


class MarkAllReadOut(BaseModel):
    ok: bool = True
    marked: int
