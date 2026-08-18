"""In-app inbox and SMTP delivery."""

from aperix_geo.services.notifications.inbox import (
    create_user_notification,
    list_user_notifications,
    mark_all_notifications_read,
    mark_notification_read,
    unread_notification_count,
)
from aperix_geo.services.notifications.smtp import send_smtp_email, smtp_configured

__all__ = [
    "create_user_notification",
    "list_user_notifications",
    "mark_all_notifications_read",
    "mark_notification_read",
    "send_smtp_email",
    "smtp_configured",
    "unread_notification_count",
]
