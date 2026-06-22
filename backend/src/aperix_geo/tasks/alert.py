"""Celery tasks: provider billing / quota alerts."""

from __future__ import annotations

import logging
from typing import Any

from aperix_geo.celery_app import celery_app
from aperix_geo.config import get_settings
from aperix_geo.services.alerts.billing import ProviderBillingEvent
from aperix_geo.services.alerts.email import send_alert_email
from aperix_geo.services.alerts.sms import send_alert_sms
from aperix_geo.services.alerts.templates import (
    billing_alert_email,
    billing_alert_sms,
    billing_recovery_email,
    billing_recovery_sms,
)

logger = logging.getLogger(__name__)


def deliver_provider_billing_alert(payload: dict[str, Any]) -> None:
    settings = get_settings()
    event = ProviderBillingEvent(**payload["event"])
    channels = set(payload.get("channels") or [])
    email_to = list(payload.get("email_to") or [])
    sms_phones = list(payload.get("sms_phones") or [])
    env_label = str(payload.get("env_label") or settings.env)
    kind = str(payload.get("kind") or "billing")

    if kind == "recovery":
        if "email" in channels and email_to:
            subject, body = billing_recovery_email(event.provider_id, env_label=env_label)
            send_alert_email(settings, to_addrs=email_to, subject=subject, body=body)
        if "sms" in channels and sms_phones:
            text = billing_recovery_sms(event.provider_id, env_label=env_label)
            for phone in sms_phones:
                send_alert_sms(settings, phone_cn11=phone, text=text, provider_id=event.provider_id)
        return

    if "email" in channels and email_to:
        subject, body = billing_alert_email(event, env_label=env_label)
        send_alert_email(settings, to_addrs=email_to, subject=subject, body=body)
    if "sms" in channels and sms_phones:
        text = billing_alert_sms(event, env_label=env_label)
        for phone in sms_phones:
            send_alert_sms(settings, phone_cn11=phone, text=text, provider_id=event.provider_id)


@celery_app.task(name="aperix_geo.tasks.alert.send_provider_billing")
def send_provider_billing(payload: dict[str, Any]) -> None:
    try:
        deliver_provider_billing_alert(payload)
    except Exception:
        logger.exception("Provider billing alert delivery failed")
