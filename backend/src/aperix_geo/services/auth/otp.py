"""SMS / email verification codes stored in Redis; 手机验证码可走阿里云短信。"""

from __future__ import annotations

import logging
import secrets
from typing import Literal

import redis

from aperix_geo.config import Settings
from aperix_geo.utils.contact import normalize_email, normalize_phone_cn

logger = logging.getLogger(__name__)

Purpose = Literal["register", "login"]
Channel = Literal["email", "phone"]


def is_dev_environment(settings: Settings) -> bool:
    return settings.env.strip().lower() in {"development", "dev", "local"}


def sms_use_dev_stub(settings: Settings) -> bool:
    """development / dev / local：手机号不走真实短信网关。"""
    return is_dev_environment(settings)


def _redis(settings: Settings) -> redis.Redis:
    return redis.from_url(settings.redis_url, decode_responses=True)


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
    写入 Redis 验证码。
    手机通道：开发环境（ENV=development|dev|local）生成随机验证码并回显，不调用阿里云；
    非开发且 SMS_ALIYUN_ENABLED=true 时调用阿里云 SendSms。
    返回 (是否已写入, 可在 JSON 中回显的验证码)。
    """
    if channel == "email":
        target = normalize_email(target_raw)
    else:
        target = normalize_phone_cn(target_raw)

    r = _redis(settings)
    cd_key = _cooldown_key(purpose, channel, target)
    if r.exists(cd_key):
        raise ValueError("发送过于频繁，请稍后再试")

    code = generate_code(settings)
    otp_key = _otp_key(purpose, channel, target)
    r.setex(otp_key, settings.otp_code_ttl_seconds, code)
    r.setex(cd_key, settings.otp_send_interval_seconds, "1")

    if channel == "email":
        logger.info("OTP email (stub) to=%s purpose=%s (dev: code=%s)", target, purpose, code)
    elif channel == "phone" and sms_use_dev_stub(settings):
        logger.info("OTP SMS dev stub (no Aliyun) to=%s purpose=%s code=%s", target, purpose, code)
    elif settings.sms_aliyun_enabled:
        try:
            from aperix_geo.services.auth import sms

            sms.send_verification_sms(settings, phone_cn11=target, code=code)
        except Exception:
            r.delete(otp_key)
            r.delete(cd_key)
            raise
    else:
        logger.info("OTP SMS (stub, set SMS_ALIYUN_ENABLED=true for Aliyun) to=%s purpose=%s code=%s", target, purpose, code)

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

    r = _redis(settings)
    otp_key = _otp_key(purpose, channel, target)
    stored = r.get(otp_key)
    if not stored or stored.strip() != code.strip():
        return False
    r.delete(otp_key)
    return True
