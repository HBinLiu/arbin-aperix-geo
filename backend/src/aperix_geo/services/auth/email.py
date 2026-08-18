"""Email OTP delivery via SMTP."""

from __future__ import annotations

import logging

from aperix_geo.config import Settings
from aperix_geo.services.notifications.smtp import send_smtp_email, smtp_configured

logger = logging.getLogger(__name__)

_PURPOSE_LABEL = {
    "login": "登录",
    "bind": "绑定邮箱",
    "invite": "邀请成员",
}


def send_verification_email(
    settings: Settings,
    *,
    email: str,
    code: str,
    purpose: str,
) -> None:
    if not smtp_configured(settings):
        raise RuntimeError("邮箱验证码未配置 SMTP（请设置 SMTP_HOST 与 SMTP_FROM 或 SMTP_USER）")

    label = _PURPOSE_LABEL.get(purpose, "验证")
    ttl_min = max(1, int(settings.otp_code_ttl_seconds) // 60)
    subject = f"【Aperix】{label}验证码"
    body = (
        f"您好，\n\n"
        f"您正在进行 Aperix {label}，验证码为：\n\n"
        f"  {code}\n\n"
        f"验证码 {ttl_min} 分钟内有效，请勿泄露给他人。\n"
        f"如非本人操作，请忽略本邮件。\n"
    )
    send_smtp_email(settings, to_addrs=[email], subject=subject, body=body)
    logger.info("OTP email sent to=%s purpose=%s", email, purpose)
