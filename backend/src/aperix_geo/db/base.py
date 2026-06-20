"""SQLAlchemy declarative base with soft-delete support."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import Boolean
from sqlalchemy import text as sa_text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utc_now() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    deleted: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=sa_text("false"),
    )

    @property
    def is_deleted(self) -> bool:
        return bool(self.deleted)

    def soft_delete(self) -> None:
        self.deleted = True
