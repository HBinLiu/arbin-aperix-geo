"""SMTP email delivery for operational alerts."""

from __future__ import annotations

import logging

from aperix_geo.config import Settings
from aperix_geo.services.notifications.smtp import send_smtp_email

logger = logging.getLogger(__name__)


def send_alert_email(settings: Settings, *, to_addrs: list[str], subject: str, body: str) -> None:
    try:
        send_smtp_email(settings, to_addrs=to_addrs, subject=subject, body=body)
    except Exception as exc:
        raise RuntimeError(f"Alert email: {exc}") from exc
    logger.info("Alert email sent subject=%s to=%s", subject, to_addrs)
