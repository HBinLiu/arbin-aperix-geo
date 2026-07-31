"""SMS / email verification codes stored in Redis; 手机走阿里云，邮箱走 SMTP。"""

from __future__ import annotations

import logging
import secrets
from datetime import datetime, timedelta
from typing import Literal
from zoneinfo import ZoneInfo

from aperix_geo.config import Settings
from aperix_geo.utils.cache.redis_kv import require_redis_client
from aperix_geo.utils.contact import normalize_email, normalize_phone_cn

logger = logging.getLogger(__name__)

Purpose = Literal["login", "bind", "invite"]
Channel = Literal["email", "phone"]

_CN_TZ = ZoneInfo("Asia/Shanghai")
_RATE_LIMIT_MSG = "发送过于频繁，请稍后再试"


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


def _day_stamp(now: datetime | None = None) -> str:
    return (now or datetime.now(_CN_TZ)).strftime("%Y%m%d")


def _hour_stamp(now: datetime | None = None) -> str:
    return (now or datetime.now(_CN_TZ)).strftime("%Y%m%d%H")


def _ttl_until_cn_day_end(now: datetime | None = None) -> int:
    current = now or datetime.now(_CN_TZ)
    tomorrow = (current + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    return max(60, int((tomorrow - current).total_seconds()))


def _ttl_until_cn_hour_end(now: datetime | None = None) -> int:
    current = now or datetime.now(_CN_TZ)
    nxt = (current + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
    return max(60, int((nxt - current).total_seconds()))


def _redis_count(r, key: str) -> int:
    raw = r.get(key)
    if raw is None:
        return 0
    try:
        return int(raw)
    except (TypeError, ValueError):
        return 0


def _incr_with_ttl(r, key: str, ttl_seconds: int) -> int:
    n = int(r.incr(key))
    if n == 1:
        r.expire(key, ttl_seconds)
    return n


def _target_day_key(channel: Channel, target_norm: str, day: str) -> str:
    return f"aperix:otp_day:v1:{channel}:{target_norm}:{day}"


def _ip_hour_key(ip: str, hour: str) -> str:
    return f"aperix:otp_ip_h:v1:{ip}:{hour}"


def _ip_day_key(ip: str, day: str) -> str:
    return f"aperix:otp_ip_d:v1:{ip}:{day}"


def _sms_global_day_key(day: str) -> str:
    return f"aperix:otp_sms_global:v1:{day}"


def _assert_rate_limits(
    *,
    r,
    settings: Settings,
    channel: Channel,
    target_norm: str,
    client_ip: str,
) -> None:
    """发码前检查；超限抛 ValueError（路由映射 429）。"""
    day = _day_stamp()
    hour = _hour_stamp()
    ip = (client_ip or "").strip() or "unknown"

    target_daily_limit = (
        settings.otp_phone_daily_limit if channel == "phone" else settings.otp_email_daily_limit
    )
    if target_daily_limit > 0:
        if _redis_count(r, _target_day_key(channel, target_norm, day)) >= target_daily_limit:
            raise ValueError(_RATE_LIMIT_MSG)

    if settings.otp_ip_hourly_limit > 0:
        if _redis_count(r, _ip_hour_key(ip, hour)) >= settings.otp_ip_hourly_limit:
            raise ValueError(_RATE_LIMIT_MSG)

    if settings.otp_ip_daily_limit > 0:
        if _redis_count(r, _ip_day_key(ip, day)) >= settings.otp_ip_daily_limit:
            raise ValueError(_RATE_LIMIT_MSG)

    if channel == "phone" and settings.otp_sms_global_daily_limit > 0:
        if _redis_count(r, _sms_global_day_key(day)) >= settings.otp_sms_global_daily_limit:
            raise ValueError(_RATE_LIMIT_MSG)


def _record_rate_limits(
    *,
    r,
    settings: Settings,
    channel: Channel,
    target_norm: str,
    client_ip: str,
) -> None:
    """投递成功后计数（冷却仍在发码流程内单独 setex）。"""
    day = _day_stamp()
    hour = _hour_stamp()
    ip = (client_ip or "").strip() or "unknown"
    day_ttl = _ttl_until_cn_day_end()
    hour_ttl = _ttl_until_cn_hour_end()

    target_daily_limit = (
        settings.otp_phone_daily_limit if channel == "phone" else settings.otp_email_daily_limit
    )
    if target_daily_limit > 0:
        _incr_with_ttl(r, _target_day_key(channel, target_norm, day), day_ttl)

    if settings.otp_ip_hourly_limit > 0:
        _incr_with_ttl(r, _ip_hour_key(ip, hour), hour_ttl)

    if settings.otp_ip_daily_limit > 0:
        _incr_with_ttl(r, _ip_day_key(ip, day), day_ttl)

    if channel == "phone" and settings.otp_sms_global_daily_limit > 0:
        _incr_with_ttl(r, _sms_global_day_key(day), day_ttl)


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
    client_ip: str = "",
) -> tuple[bool, str | None]:
    """
    写入 Redis 验证码并按通道投递。

    - 开发环境（ENV=development|dev|local）：不发真实短信/邮件，API 可回显 ``dev_code``。
    - 生产邮箱：需配置 SMTP；生产手机：需配置阿里云短信密钥/签名/模板（配齐即发，无需额外开关）。
    - 多维限流在投递前检查，成功后再计数；冷却在写入 OTP 时设置。
    返回 (是否已写入, 可在 JSON 中回显的验证码)。
    """
    if channel == "email":
        target = normalize_email(target_raw)
    else:
        target = normalize_phone_cn(target_raw)

    r = require_redis_client()
    cd_key = _cooldown_key(purpose, channel, target)
    if r.exists(cd_key):
        raise ValueError(_RATE_LIMIT_MSG)

    _assert_rate_limits(
        r=r,
        settings=settings,
        channel=channel,
        target_norm=target,
        client_ip=client_ip,
    )

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

    _record_rate_limits(
        r=r,
        settings=settings,
        channel=channel,
        target_norm=target,
        client_ip=client_ip,
    )

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
