"""Enqueue provider billing alerts."""

from __future__ import annotations

import logging
from dataclasses import asdict

from aperix_geo.config import Settings, get_settings
from aperix_geo.services.alerts.billing import (
    ProviderBillingEvent,
    classify_billing_error,
    infer_provider_role,
    is_billing_provider_error,
    provider_id_from_message,
)
from aperix_geo.services.alerts.state import evaluate_alert_gate, mark_alert_sent, mark_provider_recovered

logger = logging.getLogger(__name__)


def _env_label(settings: Settings) -> str:
    return (settings.provider_alert_env_label or settings.env or "unknown").strip()


def _alert_enabled(settings: Settings) -> bool:
    if not settings.provider_alert_enabled:
        return False
    if settings.env.strip().lower() in {"development", "dev", "local"}:
        return settings.provider_alert_enabled
    return True


def _parse_channels(raw: str) -> set[str]:
    return {part.strip().lower() for part in raw.split(",") if part.strip()}


def _parse_recipients(raw: str) -> list[str]:
    return [part.strip() for part in raw.split(",") if part.strip()]


def maybe_report_provider_billing_alert(
    message: str,
    *,
    status_code: int | None = None,
    provider_id: str | None = None,
    provider_role: str | None = None,
    settings: Settings | None = None,
) -> None:
    settings = settings or get_settings()
    if not _alert_enabled(settings):
        return
    if not is_billing_provider_error(message, status_code):
        return

    resolved_id = provider_id or provider_id_from_message(message)
    role = provider_role or infer_provider_role(resolved_id)

    gate = evaluate_alert_gate(
        resolved_id,
        min_fails=settings.provider_alert_min_fails,
        cooldown_seconds=settings.provider_alert_cooldown_seconds,
    )
    if not gate.should_notify:
        return

    event = classify_billing_error(
        message,
        status_code=status_code,
        provider_id=resolved_id,
        provider_role=role,
        fail_count=gate.fail_count,
    )
    if event is None:
        return

    mark_alert_sent(resolved_id)
    _enqueue_alert(
        event,
        channels=_parse_channels(settings.provider_alert_channels),
        email_to=_parse_recipients(settings.provider_alert_email_to),
        sms_phones=_parse_recipients(settings.provider_alert_sms_phones),
        env_label=_env_label(settings),
        kind="billing",
    )


def maybe_report_provider_success(
    provider_id: str,
    *,
    settings: Settings | None = None,
) -> None:
    settings = settings or get_settings()
    if not _alert_enabled(settings):
        return
    if not mark_provider_recovered(provider_id):
        return
    _enqueue_alert(
        ProviderBillingEvent(
            provider_id=provider_id,
            provider_role=infer_provider_role(provider_id),
            alert_kind="billing",
            status_code=None,
            message="",
            fail_count=0,
        ),
        channels=_parse_channels(settings.provider_alert_channels),
        email_to=_parse_recipients(settings.provider_alert_email_to),
        sms_phones=_parse_recipients(settings.provider_alert_sms_phones),
        env_label=_env_label(settings),
        kind="recovery",
    )


def _enqueue_alert(
    event: ProviderBillingEvent,
    *,
    channels: set[str],
    email_to: list[str],
    sms_phones: list[str],
    env_label: str,
    kind: str,
) -> None:
    payload = {
        "event": asdict(event),
        "channels": sorted(channels),
        "email_to": email_to,
        "sms_phones": sms_phones,
        "env_label": env_label,
        "kind": kind,
    }
    try:
        from aperix_geo.tasks.alert import send_provider_billing

        send_provider_billing.delay(payload)
    except Exception:
        logger.warning("Failed to enqueue provider billing alert; sending inline", exc_info=True)
        try:
            from aperix_geo.tasks.alert import deliver_provider_billing_alert

            deliver_provider_billing_alert(payload)
        except Exception:
            logger.exception("Inline provider billing alert delivery failed")
