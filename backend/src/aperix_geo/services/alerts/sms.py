"""SMS delivery for operational alerts (Aliyun)."""

from __future__ import annotations

import json
import logging

from aperix_geo.config import Settings
from aperix_geo.services.alerts.templates import provider_display_name

logger = logging.getLogger(__name__)


def send_alert_sms(settings: Settings, *, phone_cn11: str, text: str, provider_id: str) -> None:
    from aperix_geo.services.auth.sms import sms_aliyun_configured

    if not sms_aliyun_configured(settings):
        logger.info("Alert SMS (stub, Aliyun not configured) to=%s provider=%s text=%s", phone_cn11, provider_id, text)
        return
    template = settings.provider_alert_sms_template_code.strip() or settings.sms_aliyun_template_code.strip()
    if not template:
        logger.warning("Alert SMS skipped: no PROVIDER_ALERT_SMS_TEMPLATE_CODE or SMS_ALIYUN_TEMPLATE_CODE")
        return

    from alibabacloud_dysmsapi20170525.client import Client as Dysmsapi20170525Client
    from alibabacloud_dysmsapi20170525 import models as dysmsapi_models
    from alibabacloud_tea_openapi import models as open_api_models
    from alibabacloud_tea_util import models as util_models

    if not settings.sms_aliyun_access_key_id or not settings.sms_aliyun_access_key_secret:
        raise RuntimeError("SMS enabled but Aliyun credentials missing")
    if not settings.sms_aliyun_sign_name:
        raise RuntimeError("SMS enabled but SMS_ALIYUN_SIGN_NAME missing")

    config = open_api_models.Config(
        access_key_id=settings.sms_aliyun_access_key_id,
        access_key_secret=settings.sms_aliyun_access_key_secret,
    )
    config.endpoint = settings.sms_aliyun_endpoint
    client = Dysmsapi20170525Client(config)

    # Prefer a dedicated alert template with platform/env vars; fall back to plain code key.
    template_param = json.dumps(
        {
            "platform": provider_display_name(provider_id),
            "message": text[:60],
        },
        ensure_ascii=False,
    )

    req = dysmsapi_models.SendSmsRequest(
        phone_numbers=phone_cn11,
        sign_name=settings.sms_aliyun_sign_name,
        template_code=template,
        template_param=template_param,
    )
    runtime = util_models.RuntimeOptions()
    resp = client.send_sms_with_options(req, runtime)
    if resp.body.code != "OK":
        raise RuntimeError(f"Aliyun SendSms failed: {resp.body.code} {resp.body.message}")
    logger.info("Alert SMS sent to=%s provider=%s", phone_cn11, provider_id)
