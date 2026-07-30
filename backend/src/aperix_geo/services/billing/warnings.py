"""AI quota threshold warnings (in-app + email + WeChat template)."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from aperix_geo.config import get_settings
from aperix_geo.db.models import TenantSubscription, User
from aperix_geo.services.alerts.email import send_alert_email
from aperix_geo.services.billing.quota import get_current_usage_period, get_subscription_snapshot
from aperix_geo.services.notifications.inbox import create_user_notification
from aperix_geo.services.wechat.config import wechat_configured
from aperix_geo.services.wechat.template import (
    build_template_data,
    quota_warn_context,
    resolve_quota_warn_template,
    send_template_message,
)
from aperix_geo.services.wechat.token import WechatError
from aperix_geo.utils.cache.redis_kv import redis_delete, redis_set_nx

logger = logging.getLogger(__name__)

_THRESHOLDS: tuple[tuple[str, float], ...] = (
    ("20pct", 0.20),
    ("5pct", 0.05),
    ("0pct", 0.0),
)

# 微信模板 const4「异常原因」枚举（须与公众平台一字不差）
_WECHAT_REASON_BY_LEVEL: dict[str, str] = {
    "20pct": "额度不足20%",
    "5pct": "额度不足5%",
    "0pct": "额度已用尽",
}

_ACTION_PATH = "/billing/plan"


@dataclass(frozen=True, slots=True)
class QuotaWarningLevel:
    code: str
    remaining_ratio: float
    available: int
    total_capacity: int


def compute_quota_warning(
    *,
    monthly_limit: int,
    monthly_remaining: int,
    usage_pack_balance: int,
    ai_requests_available: int,
) -> QuotaWarningLevel | None:
    total = max(monthly_limit, 0) + max(usage_pack_balance, 0)
    if total <= 0:
        return None
    available = max(ai_requests_available, 0)
    ratio = available / total
    warning: QuotaWarningLevel | None = None
    for code, threshold in _THRESHOLDS:
        if ratio <= threshold:
            warning = QuotaWarningLevel(
                code=code,
                remaining_ratio=ratio,
                available=available,
                total_capacity=total,
            )
    return warning


def _dedupe_key(tenant_id: str, period_id: str, level: str) -> str:
    return f"aperix:billing:quota_warn:{tenant_id}:{period_id}:{level}"


def _notify_in_app_tenant_users(
    db: Session,
    tenant_id,
    *,
    title: str,
    body: str,
    action_url: str,
    dedupe_base: str,
) -> int:
    users = db.execute(
        select(User).where(
            User.tenant_id == tenant_id,
            User.deleted.is_(False),
            User.is_active.is_(True),
            User.notify_in_app.is_(True),
        )
    ).scalars().all()
    created = 0
    for user in users:
        row = create_user_notification(
            db,
            tenant_id=tenant_id,
            user_id=user.id,
            category="billing",
            title=title,
            body=body,
            action_url=action_url,
            dedupe_key=f"{dedupe_base}:{user.id}",
        )
        if row is not None:
            created += 1
    return created


def _notify_email_tenant_users(db: Session, tenant_id, *, subject: str, body: str) -> int:
    users = db.execute(
        select(User).where(
            User.tenant_id == tenant_id,
            User.deleted.is_(False),
            User.is_active.is_(True),
            User.notify_email.is_(True),
        )
    ).scalars().all()
    emails = [u.email.strip() for u in users if u.email.strip()]
    if not emails:
        return 0
    settings = get_settings()
    if not settings.smtp_host.strip():
        return 0
    send_alert_email(settings, to_addrs=emails, subject=subject, body=body)
    return len(emails)


def _notify_wechat_tenant_users(
    db: Session,
    tenant_id,
    *,
    title: str,
    body: str,
    available: int,
    reason: str = "",
) -> int:
    settings = get_settings()
    if not wechat_configured(settings):
        return 0

    resolved = resolve_quota_warn_template(settings=settings)
    if resolved is None:
        return 0
    template, jump_url = resolved

    users = db.execute(
        select(User).where(
            User.tenant_id == tenant_id,
            User.deleted.is_(False),
            User.is_active.is_(True),
            User.notify_wechat.is_(True),
            User.open_id != "",
        )
    ).scalars().all()
    if not users:
        return 0

    sent = 0
    for user in users:
        ctx = quota_warn_context(
            title=title,
            body=body,
            available=available,
            phone=user.phone or "",
            reason=reason or title,
        )
        data = build_template_data(template, context=ctx)
        try:
            send_template_message(
                open_id=user.open_id,
                template_id=template.template_id,
                data=data,
                url=jump_url,
                settings=settings,
            )
            sent += 1
        except WechatError as exc:
            logger.warning(
                "WeChat quota warn failed user=%s openid=%s err=%s",
                user.id,
                user.open_id[:8],
                exc,
            )
        except Exception:
            logger.exception("WeChat quota warn unexpected error user=%s", user.id)
    return sent


def process_quota_warnings(db: Session, *, now: datetime | None = None) -> int:
    """Scan active tenants and notify at 20% / 5% / 0% thresholds."""
    moment = now or datetime.now(UTC)
    subscriptions = db.execute(
        select(TenantSubscription).where(
            TenantSubscription.deleted.is_(False),
            TenantSubscription.status.in_(("active", "canceled")),
            TenantSubscription.current_period_end > moment,
        )
    ).scalars().all()

    sent = 0
    for sub in subscriptions:
        try:
            snapshot = get_subscription_snapshot(db, sub.tenant_id, now=moment)
        except Exception:
            continue
        usage = snapshot.usage
        warning = compute_quota_warning(
            monthly_limit=usage.monthly_limit,
            monthly_remaining=usage.monthly_remaining,
            usage_pack_balance=usage.usage_pack_balance,
            ai_requests_available=usage.ai_requests_available,
        )
        if warning is None:
            continue

        period = get_current_usage_period(db, sub.tenant_id, now=moment)
        period_id = str(period.id) if period is not None else "none"
        dedupe = _dedupe_key(str(sub.tenant_id), period_id, warning.code)
        ttl_s = 35 * 24 * 3600
        if not redis_set_nx(dedupe, ttl_s=ttl_s, fail_open=False):
            continue

        if warning.code == "0pct":
            email_subject = "Aperix AI：AI 请求额度已用尽"
            in_app_title = "AI 请求额度已用尽"
            body = (
                f"租户 {snapshot.plan_name} 的 AI 请求额度已用尽。\n"
                f"请升级订阅或购买配额包以继续使用 AI 功能。"
            )
        elif warning.code == "5pct":
            email_subject = "Aperix AI：AI 请求额度即将用尽（剩余 5%）"
            in_app_title = "AI 请求额度即将用尽"
            body = (
                f"当前可用 AI 请求：{warning.available} 次（约 {warning.remaining_ratio:.0%} 剩余）。\n"
                f"建议尽快升级订阅或购买配额包。"
            )
        else:
            email_subject = "Aperix AI：AI 请求额度剩余不足 20%"
            in_app_title = "AI 请求额度剩余不足 20%"
            body = (
                f"当前可用 AI 请求：{warning.available} 次（约 {warning.remaining_ratio:.0%} 剩余）。\n"
                f"可在「订阅与账单」查看用量或购买配额包。"
            )

        in_app_body = body.replace("\n", " ")
        in_app_n = _notify_in_app_tenant_users(
            db,
            sub.tenant_id,
            title=in_app_title,
            body=in_app_body,
            action_url=_ACTION_PATH,
            dedupe_base=dedupe,
        )
        email_n = _notify_email_tenant_users(
            db, sub.tenant_id, subject=email_subject, body=body
        )
        wechat_n = _notify_wechat_tenant_users(
            db,
            sub.tenant_id,
            title=in_app_title,
            body=in_app_body,
            available=warning.available,
            reason=_WECHAT_REASON_BY_LEVEL.get(warning.code, "额度不足20%"),
        )

        if in_app_n + email_n + wechat_n > 0:
            sent += 1
            logger.info(
                "AI 额度预警已发送 tenant=%s level=%s in_app=%d email=%d wechat=%d",
                sub.tenant_id,
                warning.code,
                in_app_n,
                email_n,
                wechat_n,
            )
        else:
            redis_delete(dedupe)
    return sent
