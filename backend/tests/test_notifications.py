"""Tests for in-app notification inbox."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock

from aperix_geo.db.models import EPOCH, UserNotification
from aperix_geo.services.notifications.inbox import (
    create_user_notification,
    is_unread,
    mark_all_notifications_read,
    mark_notification_read,
    unread_notification_count,
)


def test_is_unread_uses_epoch_sentinel() -> None:
    row = UserNotification(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        category="billing",
        title="test",
        read_at=EPOCH,
    )
    assert is_unread(row) is True


def test_unread_notification_count() -> None:
    db = MagicMock()
    db.scalar.return_value = 3
    assert unread_notification_count(db, uuid.uuid4()) == 3


def test_mark_notification_read_updates_row() -> None:
    user_id = uuid.uuid4()
    row = UserNotification(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        user_id=user_id,
        category="billing",
        title="test",
        read_at=EPOCH,
    )
    db = MagicMock()
    db.execute.return_value.scalar_one_or_none.return_value = row

    result = mark_notification_read(db, user_id=user_id, notification_id=row.id)

    assert result is row
    assert not is_unread(row)
    db.flush.assert_called_once()


def test_mark_all_notifications_read() -> None:
    db = MagicMock()
    db.execute.return_value.rowcount = 2
    assert mark_all_notifications_read(db, user_id=uuid.uuid4()) == 2


def test_create_user_notification_skips_existing_dedupe() -> None:
    user_id = uuid.uuid4()
    existing = UserNotification(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        user_id=user_id,
        category="billing",
        title="old",
        dedupe_key="billing:quota:1",
    )
    db = MagicMock()
    db.execute.return_value.scalar_one_or_none.return_value = existing

    row = create_user_notification(
        db,
        tenant_id=existing.tenant_id,
        user_id=user_id,
        category="billing",
        title="new",
        dedupe_key="billing:quota:1",
    )

    assert row is existing
    db.add.assert_not_called()
