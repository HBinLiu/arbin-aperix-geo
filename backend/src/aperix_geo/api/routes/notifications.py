"""User in-app notification routes."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from aperix_geo.api.deps import CurrentUser, DbSession
from aperix_geo.schemas.notifications import (
    MarkAllReadOut,
    MarkReadOut,
    NotificationListOut,
    NotificationOut,
    UnreadCountOut,
)
from aperix_geo.services.notifications.inbox import (
    is_unread,
    list_user_notifications,
    mark_all_notifications_read,
    mark_notification_read,
    unread_notification_count,
)

router = APIRouter(prefix="/notifications", tags=["notifications"])


def _to_out(row) -> NotificationOut:
    return NotificationOut(
        id=row.id,
        category=row.category,
        title=row.title,
        body=row.body,
        action_url=row.action_url,
        read=not is_unread(row),
        created_at=row.created_at,
    )


@router.get("", response_model=NotificationListOut)
def list_notifications(
    current: CurrentUser,
    db: DbSession,
    limit: int = Query(default=20, ge=1, le=50),
) -> NotificationListOut:
    rows = list_user_notifications(db, current.id, limit=limit)
    unread = unread_notification_count(db, current.id)
    return NotificationListOut(items=[_to_out(row) for row in rows], unread_count=unread)


@router.get("/unread-count", response_model=UnreadCountOut)
def get_unread_count(current: CurrentUser, db: DbSession) -> UnreadCountOut:
    return UnreadCountOut(unread_count=unread_notification_count(db, current.id))


@router.patch("/{notification_id}/read", response_model=MarkReadOut)
def mark_read(
    notification_id: UUID,
    current: CurrentUser,
    db: DbSession,
) -> MarkReadOut:
    row = mark_notification_read(db, user_id=current.id, notification_id=notification_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    db.commit()
    return MarkReadOut(id=row.id, read=True)


@router.post("/read-all", response_model=MarkAllReadOut)
def mark_all_read(current: CurrentUser, db: DbSession) -> MarkAllReadOut:
    marked = mark_all_notifications_read(db, user_id=current.id)
    db.commit()
    return MarkAllReadOut(marked=marked)
