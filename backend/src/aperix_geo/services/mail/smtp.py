"""Shared SMTP send helper."""

from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage
from email.utils import formataddr

from aperix_geo.config import Settings

logger = logging.getLogger(__name__)


def smtp_configured(settings: Settings) -> bool:
    return bool(
        settings.smtp_host.strip()
        and (settings.smtp_from.strip() or settings.smtp_user.strip())
    )


def send_smtp_email(
    settings: Settings,
    *,
    to_addrs: list[str],
    subject: str,
    body: str,
) -> None:
    if not settings.smtp_host.strip() or not to_addrs:
        raise RuntimeError("SMTP_HOST or recipients missing")
    from_addr = settings.smtp_from.strip() or settings.smtp_user.strip()
    if not from_addr:
        raise RuntimeError("SMTP_FROM / SMTP_USER missing")

    msg = EmailMessage()
    msg["Subject"] = subject
    from_name = settings.smtp_from_name.strip()
    msg["From"] = formataddr((from_name, from_addr)) if from_name else from_addr
    msg["To"] = ", ".join(to_addrs)
    msg.set_content(body)

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30) as smtp:
        if settings.smtp_use_tls:
            smtp.starttls()
        if settings.smtp_user.strip():
            smtp.login(settings.smtp_user, settings.smtp_password)
        smtp.send_message(msg)
    logger.info("SMTP email sent subject=%s to=%s", subject, to_addrs)
