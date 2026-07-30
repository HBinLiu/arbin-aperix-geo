"""Celery tasks: provider billing / quota alerts (email)."""

from __future__ import annotations

import logging
from typing import Any

from aperix_geo.celery_app import celery_app
from aperix_geo.config import get_settings
from aperix_geo.services.alerts.billing import ProviderBillingEvent
from aperix_geo.services.alerts.email import send_alert_email
from aperix_geo.services.alerts.templates import billing_alert_email, billing_recovery_email

logger = logging.getLogger(__name__)


def deliver_provider_billing_alert(payload: dict[str, Any]) -> None:
    settings = get_settings()
    event = ProviderBillingEvent(**payload["event"])
    email_to = list(payload.get("email_to") or [])
    if not email_to:
        return
    env = (settings.env or "unknown").strip()
    kind = str(payload.get("kind") or "billing")

    if kind == "recovery":
        subject, body = billing_recovery_email(event.provider_id, env=env)
    else:
        subject, body = billing_alert_email(event, env=env)
    send_alert_email(settings, to_addrs=email_to, subject=subject, body=body)


@celery_app.task(name="aperix_geo.tasks.alert.send_provider_billing")
def send_provider_billing(payload: dict[str, Any]) -> None:
    try:
        deliver_provider_billing_alert(payload)
    except Exception:
        logger.exception("Provider billing alert delivery failed")
