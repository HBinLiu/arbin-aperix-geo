"""阿里云短信服务（SendSms）。需在控制台创建签名与模板，模板内需包含验证码变量（默认 JSON 键 `code`）。"""

from __future__ import annotations

import json
import logging

from aperix_geo.config import Settings

logger = logging.getLogger(__name__)


def sms_aliyun_configured(settings: Settings) -> bool:
    """True when Aliyun SMS credentials + sign + OTP template are present (like SMTP)."""
    return bool(
        settings.sms_aliyun_access_key_id.strip()
        and settings.sms_aliyun_access_key_secret.strip()
        and settings.sms_aliyun_sign_name.strip()
        and settings.sms_aliyun_template_code.strip()
    )


def send_verification_sms(settings: Settings, *, phone_cn11: str, code: str) -> None:
    """
    发送国内短信。phone_cn11 为 11 位数字（不含 +86）。
    模板变量默认：`{"code": "<验证码>"}`，可通过 `SMS_ALIYUN_TEMPLATE_PARAM_CODE_KEY` 改键名。
    """
    if not settings.sms_aliyun_access_key_id or not settings.sms_aliyun_access_key_secret:
        raise RuntimeError("阿里云短信未配置 ACCESS_KEY_ID / ACCESS_KEY_SECRET")
    if not settings.sms_aliyun_sign_name or not settings.sms_aliyun_template_code:
        raise RuntimeError("阿里云短信未配置 SIGN_NAME 或 TEMPLATE_CODE")

    from alibabacloud_dysmsapi20170525.client import Client as Dysmsapi20170525Client
    from alibabacloud_dysmsapi20170525 import models as dysmsapi_models
    from alibabacloud_tea_openapi import models as open_api_models
    from alibabacloud_tea_util import models as util_models

    config = open_api_models.Config(
        access_key_id=settings.sms_aliyun_access_key_id,
        access_key_secret=settings.sms_aliyun_access_key_secret,
    )
    config.endpoint = settings.sms_aliyun_endpoint
    client = Dysmsapi20170525Client(config)

    param_key = settings.sms_aliyun_template_param_code_key
    template_param = json.dumps({param_key: code}, ensure_ascii=False)

    req = dysmsapi_models.SendSmsRequest(
        phone_numbers=phone_cn11,
        sign_name=settings.sms_aliyun_sign_name,
        template_code=settings.sms_aliyun_template_code,
        template_param=template_param,
    )
    runtime = util_models.RuntimeOptions()
    try:
        resp = client.send_sms_with_options(req, runtime)
    except Exception as e:
        logger.exception("Aliyun SendSms request failed: %s", e)
        raise RuntimeError(f"阿里云短信请求失败: {e}") from e

    body = resp.body
    if body is None:
        raise RuntimeError("阿里云短信返回空 body")
    biz_code = getattr(body, "code", None) or getattr(body, "Code", None)
    biz_msg = getattr(body, "message", None) or getattr(body, "Message", None)
    if biz_code != "OK":
        raise RuntimeError(f"阿里云短信业务错误: {biz_code} {biz_msg or ''}".strip())
    logger.info("Aliyun SMS sent ok to=%s", phone_cn11)
