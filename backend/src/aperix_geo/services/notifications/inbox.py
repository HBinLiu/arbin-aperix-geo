"""In-app notification inbox CRUD."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from aperix_geo.db.models import EPOCH, UserNotification


def utc_now() -> datetime:
    return datetime.now(UTC)


def is_unread(row: UserNotification) -> bool:
    return row.read_at <= EPOCH


def create_user_notification(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    category: str,
    title: str,
    body: str = "",
    action_url: str = "",
    dedupe_key: str = "",
) -> UserNotification | None:
    """Insert a notification; skip duplicate when ``dedupe_key`` is set."""
    key = dedupe_key.strip()
    if key:
        existing = db.execute(
            select(UserNotification)
            .where(
                UserNotification.user_id == user_id,
                UserNotification.dedupe_key == key,
                UserNotification.deleted.is_(False),
            )
            .limit(1)
        ).scalar_one_or_none()
        if existing is not None:
            return existing

    row = UserNotification(
        tenant_id=tenant_id,
        user_id=user_id,
        category=category.strip(),
        title=title.strip(),
        body=body.strip(),
        action_url=action_url.strip(),
        dedupe_key=key,
    )
    try:
        with db.begin_nested():
            db.add(row)
            db.flush()
    except IntegrityError:
        if not key:
            raise
        return db.execute(
            select(UserNotification)
            .where(
                UserNotification.user_id == user_id,
                UserNotification.dedupe_key == key,
                UserNotification.deleted.is_(False),
            )
            .limit(1)
        ).scalar_one_or_none()
    return row


def list_user_notifications(
    db: Session,
    user_id: uuid.UUID,
    *,
    limit: int = 20,
) -> list[UserNotification]:
    capped = max(1, min(limit, 50))
    return list(
        db.execute(
            select(UserNotification)
            .where(
                UserNotification.user_id == user_id,
                UserNotification.deleted.is_(False),
            )
            .order_by(UserNotification.created_at.desc())
            .limit(capped)
        ).scalars()
    )


def unread_notification_count(db: Session, user_id: uuid.UUID) -> int:
    return int(
        db.scalar(
            select(func.count())
            .select_from(UserNotification)
            .where(
                UserNotification.user_id == user_id,
                UserNotification.deleted.is_(False),
                UserNotification.read_at <= EPOCH,
            )
        )
        or 0
    )


def mark_notification_read(db: Session, *, user_id: uuid.UUID, notification_id: uuid.UUID) -> UserNotification | None:
    row = db.execute(
        select(UserNotification)
        .where(
            UserNotification.id == notification_id,
            UserNotification.user_id == user_id,
            UserNotification.deleted.is_(False),
        )
        .limit(1)
    ).scalar_one_or_none()
    if row is None:
        return None
    if is_unread(row):
        row.read_at = utc_now()
        db.flush()
    return row


def mark_all_notifications_read(db: Session, *, user_id: uuid.UUID) -> int:
    moment = utc_now()
    result = db.execute(
        update(UserNotification)
        .where(
            UserNotification.user_id == user_id,
            UserNotification.deleted.is_(False),
            UserNotification.read_at <= EPOCH,
        )
        .values(read_at=moment)
    )
    db.flush()
    return int(result.rowcount or 0)
