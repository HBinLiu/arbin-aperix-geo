"""SMS / email verification codes stored in Redis; 手机走阿里云，邮箱走 SMTP。"""

from __future__ import annotations

import logging
import secrets
from typing import Literal

from aperix_geo.config import Settings
from aperix_geo.utils.cache.redis_kv import require_redis_client
from aperix_geo.utils.contact import normalize_email, normalize_phone_cn

logger = logging.getLogger(__name__)

Purpose = Literal["login", "bind", "invite"]
Channel = Literal["email", "phone"]


def is_dev_environment(settings: Settings) -> bool:
    return settings.env.strip().lower() in {"development", "dev", "local"}


def sms_use_dev_stub(settings: Settings) -> bool:
    """development / dev / local：手机号不走真实短信网关。"""
    return is_dev_environment(settings)


def email_use_dev_stub(settings: Settings) -> bool:
    """development / dev / local：邮箱不走真实 SMTP。"""
    return is_dev_environment(settings)


def _otp_key(purpose: Purpose, channel: Channel, target_norm: str) -> str:
    return f"aperix:otp:v1:{purpose}:{channel}:{target_norm}"


def _cooldown_key(purpose: Purpose, channel: Channel, target_norm: str) -> str:
    return f"aperix:otp_cd:v1:{purpose}:{channel}:{target_norm}"


def generate_code(settings: Settings) -> str:
    length = settings.otp_code_length
    lo = 10 ** (length - 1)
    hi = 10**length - 1
    return str(secrets.randbelow(hi - lo + 1) + lo)


def send_code(
    *,
    settings: Settings,
    purpose: Purpose,
    channel: Channel,
    target_raw: str,
) -> tuple[bool, str | None]:
    """
    写入 Redis 验证码并按通道投递。

    - 开发环境（ENV=development|dev|local）：不发真实短信/邮件，API 可回显 ``dev_code``。
    - 生产邮箱：需配置 SMTP；生产手机：需配置阿里云短信密钥/签名/模板（配齐即发，无需额外开关）。
    返回 (是否已写入, 可在 JSON 中回显的验证码)。
    """
    if channel == "email":
        target = normalize_email(target_raw)
    else:
        target = normalize_phone_cn(target_raw)

    r = require_redis_client()
    cd_key = _cooldown_key(purpose, channel, target)
    if r.exists(cd_key):
        raise ValueError("发送过于频繁，请稍后再试")

    code = generate_code(settings)
    otp_key = _otp_key(purpose, channel, target)
    r.setex(otp_key, settings.otp_code_ttl_seconds, code)
    r.setex(cd_key, settings.otp_send_interval_seconds, "1")

    try:
        if channel == "email":
            if email_use_dev_stub(settings):
                logger.info("OTP email dev stub to=%s purpose=%s code=%s", target, purpose, code)
            else:
                from aperix_geo.services.auth.email import send_verification_email

                send_verification_email(settings, email=target, code=code, purpose=purpose)
        elif sms_use_dev_stub(settings):
            logger.info("OTP SMS dev stub (no Aliyun) to=%s purpose=%s code=%s", target, purpose, code)
        else:
            from aperix_geo.services.auth import sms

            if not sms.sms_aliyun_configured(settings):
                raise RuntimeError(
                    "短信未配置（请设置 SMS_ALIYUN_ACCESS_KEY_ID / SECRET、SIGN_NAME、TEMPLATE_CODE）"
                )
            sms.send_verification_sms(settings, phone_cn11=target, code=code)
    except Exception:
        r.delete(otp_key)
        r.delete(cd_key)
        raise

    # 仅开发环境在 API 响应中回显验证码；生产绝不回显
    exposed = code if is_dev_environment(settings) else None
    return True, exposed


def verify_code(
    *,
    settings: Settings,
    purpose: Purpose,
    channel: Channel,
    target_raw: str,
    code: str,
) -> bool:
    if channel == "email":
        target = normalize_email(target_raw)
    else:
        target = normalize_phone_cn(target_raw)

    r = require_redis_client()
    otp_key = _otp_key(purpose, channel, target)
    stored = r.get(otp_key)
    if not stored or stored.strip() != code.strip():
        return False
    r.delete(otp_key)
    return True
