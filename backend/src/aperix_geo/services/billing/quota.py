"""Tenant subscription limits and AI request quota."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import func, select, text, update
from sqlalchemy.orm import Session

from aperix_geo.db.models import (
    EPOCH,
    Plan,
    Prompt,
    Subject,
    Tenant,
    TenantPlanOverride,
    TenantSubscription,
    TenantUsagePeriod,
    User,
    ZERO_UUID,
)
from aperix_geo.services.billing.exceptions import QuotaExceededError, SubscriptionInactiveError
from aperix_geo.services.billing.limits import PlanLimits, effective_limits
from aperix_geo.services.billing.quota_ledger import existing_consumption_pool, record_consumption
from aperix_geo.services.billing.usage_tokens import normalize_token_usage
from aperix_geo.services.sampling.frequency import (
    ALLOWED_SAMPLING_FREQUENCIES,
    normalize_sampling_frequency,
    sampling_interval_days,
)


@dataclass(frozen=True, slots=True)
class UsageSnapshot:
    subjects_count: int
    prompts_count: int
    monthly_limit: int
    monthly_used: int
    monthly_remaining: int
    usage_pack_balance: int
    ai_requests_available: int


@dataclass(frozen=True, slots=True)
class SubscriptionSnapshot:
    plan_code: str
    plan_name: str
    billing_cycle: str
    status: str
    current_period_start: datetime
    current_period_end: datetime
    ai_period_start: datetime | None
    ai_period_end: datetime | None
    subscription_active: bool
    limits: PlanLimits
    usage: UsageSnapshot


def utc_now() -> datetime:
    return datetime.now(UTC)


def subscription_is_usable(subscription: TenantSubscription, *, now: datetime | None = None) -> bool:
    moment = now or utc_now()
    if subscription.status == "expired":
        return False
    if subscription.status in ("active", "canceled"):
        return moment < subscription.current_period_end
    return False


def get_current_usage_period(db: Session, tenant_id: uuid.UUID, *, now: datetime | None = None) -> TenantUsagePeriod | None:
    moment = now or utc_now()
    return db.execute(
        select(TenantUsagePeriod)
        .where(
            TenantUsagePeriod.tenant_id == tenant_id,
            TenantUsagePeriod.deleted.is_(False),
            TenantUsagePeriod.period_start <= moment,
            TenantUsagePeriod.period_end > moment,
        )
        .order_by(TenantUsagePeriod.period_start.desc())
        .limit(1)
    ).scalar_one_or_none()


def _load_subscription(db: Session, tenant_id: uuid.UUID) -> TenantSubscription:
    subscription = db.execute(
        select(TenantSubscription)
        .where(
            TenantSubscription.tenant_id == tenant_id,
            TenantSubscription.deleted.is_(False),
        )
        .limit(1)
    ).scalar_one_or_none()
    if subscription is None:
        raise SubscriptionInactiveError("Subscription not found")
    return subscription


def _load_subscription_context(
    db: Session, tenant_id: uuid.UUID
) -> tuple[Tenant, TenantSubscription, Plan, TenantPlanOverride | None]:
    tenant = db.get(Tenant, tenant_id)
    if tenant is None or tenant.deleted:
        raise SubscriptionInactiveError("Tenant not found")

    subscription = _load_subscription(db, tenant_id)

    plan = db.get(Plan, subscription.plan_id)
    if plan is None or plan.deleted:
        raise SubscriptionInactiveError("Plan not found")

    override = db.execute(
        select(TenantPlanOverride)
        .where(
            TenantPlanOverride.tenant_id == tenant_id,
            TenantPlanOverride.deleted.is_(False),
        )
        .limit(1)
    ).scalar_one_or_none()

    return tenant, subscription, plan, override


def _count_subjects(db: Session, tenant_id: uuid.UUID) -> int:
    return int(
        db.scalar(
            select(func.count())
            .select_from(Subject)
            .where(Subject.tenant_id == tenant_id, Subject.deleted.is_(False))
        )
        or 0
    )


def _count_prompts(db: Session, tenant_id: uuid.UUID) -> int:
    return int(
        db.scalar(
            select(func.count())
            .select_from(Prompt)
            .join(Subject, Subject.id == Prompt.subject_id)
            .where(Subject.tenant_id == tenant_id, Subject.deleted.is_(False), Prompt.deleted.is_(False))
        )
        or 0
    )


def _build_usage_snapshot(
    db: Session,
    tenant: Tenant,
    limits: PlanLimits,
    usage_period: TenantUsagePeriod | None,
) -> UsageSnapshot:
    monthly_limit = usage_period.monthly_limit if usage_period is not None else limits.per_month_usages
    monthly_used = usage_period.monthly_used if usage_period is not None else 0
    monthly_remaining = max(monthly_limit - monthly_used, 0)
    pack_balance = tenant.usage_pack_balance
    return UsageSnapshot(
        subjects_count=_count_subjects(db, tenant.id),
        prompts_count=_count_prompts(db, tenant.id),
        monthly_limit=monthly_limit,
        monthly_used=monthly_used,
        monthly_remaining=monthly_remaining,
        usage_pack_balance=pack_balance,
        ai_requests_available=monthly_remaining + pack_balance,
    )


def get_subscription_snapshot(db: Session, tenant_id: uuid.UUID, *, now: datetime | None = None) -> SubscriptionSnapshot:
    moment = now or utc_now()
    tenant, subscription, plan, override = _load_subscription_context(db, tenant_id)
    limits = effective_limits(plan, override)
    usage_period = get_current_usage_period(db, tenant_id, now=moment)
    return SubscriptionSnapshot(
        plan_code=plan.code,
        plan_name=plan.name,
        billing_cycle=subscription.billing_cycle,
        status=subscription.status,
        current_period_start=subscription.current_period_start,
        current_period_end=subscription.current_period_end,
        ai_period_start=usage_period.period_start if usage_period else None,
        ai_period_end=usage_period.period_end if usage_period else None,
        subscription_active=subscription_is_usable(subscription, now=moment),
        limits=limits,
        usage=_build_usage_snapshot(db, tenant, limits, usage_period),
    )


def get_limits_for_tenant(db: Session, tenant_id: uuid.UUID) -> PlanLimits:
    _, _, plan, override = _load_subscription_context(db, tenant_id)
    return effective_limits(plan, override)


def _active_competitor_count(subject: Subject) -> int:
    return sum(1 for row in subject.competitors or [] if not row.deleted)


def assert_can_create_subject(db: Session, tenant_id: uuid.UUID) -> None:
    require_active_subscription(db, tenant_id)
    limits = get_limits_for_tenant(db, tenant_id)
    if _count_subjects(db, tenant_id) + 1 > limits.max_subjects:
        raise QuotaExceededError(
            dimension="max_subjects",
            message=f"品牌数量已达上限（{limits.max_subjects} 个）",
        )


def _count_tenant_members(db: Session, tenant_id: uuid.UUID) -> int:
    return int(
        db.scalar(
            select(func.count())
            .select_from(User)
            .where(User.tenant_id == tenant_id, User.deleted.is_(False))
        )
        or 0
    )


def assert_team_member_capacity(db: Session, tenant_id: uuid.UUID, *, adding: int = 1) -> None:
    require_active_subscription(db, tenant_id)
    limits = get_limits_for_tenant(db, tenant_id)
    if _count_tenant_members(db, tenant_id) + adding > limits.max_team_members:
        raise QuotaExceededError(
            dimension="max_team_members",
            message=f"团队席位已达上限（{limits.max_team_members} 个）",
        )


def assert_subject_sampling_frequency(db: Session, tenant_id: uuid.UUID, frequency: str) -> str:
    require_active_subscription(db, tenant_id)
    code = normalize_sampling_frequency(frequency)
    if code not in ALLOWED_SAMPLING_FREQUENCIES:
        raise QuotaExceededError(
            dimension="sampling_frequency",
            message="无效的采样间隔",
        )
    limits = get_limits_for_tenant(db, tenant_id)
    plan_days = sampling_interval_days(limits.sampling_frequency)
    subject_days = sampling_interval_days(code)
    if subject_days < plan_days:
        raise QuotaExceededError(
            dimension="sampling_frequency",
            message=f"当前订阅不支持该采样间隔（最快每 {plan_days} 天 1 次）",
        )
    return code


def assert_competitor_capacity(
    db: Session,
    tenant_id: uuid.UUID,
    subject: Subject,
    *,
    adding: int = 1,
) -> None:
    require_active_subscription(db, tenant_id)
    limits = get_limits_for_tenant(db, tenant_id)
    if _active_competitor_count(subject) + adding > limits.max_per_competitors:
        raise QuotaExceededError(
            dimension="max_per_competitors",
            message=f"竞争对手已达上限（{limits.max_per_competitors} 个）",
        )


def assert_platform_capacity(db: Session, tenant_id: uuid.UUID, platform_count: int) -> None:
    require_active_subscription(db, tenant_id)
    limits = get_limits_for_tenant(db, tenant_id)
    if platform_count > limits.max_per_platforms:
        raise QuotaExceededError(
            dimension="max_per_platforms",
            message=f"平台数量超过上限（{limits.max_per_platforms} 个）",
        )


def remaining_prompt_slots(db: Session, tenant_id: uuid.UUID) -> int:
    limits = get_limits_for_tenant(db, tenant_id)
    used = _count_prompts(db, tenant_id)
    return max(0, limits.max_prompts_total - used)


def assert_can_add_prompts(db: Session, tenant_id: uuid.UUID, *, count: int) -> None:
    require_active_subscription(db, tenant_id)
    remaining = remaining_prompt_slots(db, tenant_id)
    if count <= remaining:
        return
    limits = get_limits_for_tenant(db, tenant_id)
    if remaining <= 0:
        raise QuotaExceededError(
            dimension="max_prompts_total",
            message=f"提示词已达上限（{limits.max_prompts_total} 条）",
        )
    raise QuotaExceededError(
        dimension="max_prompts_total",
        message=f"仅剩 {remaining} 个提示词额度",
    )


def require_active_subscription(db: Session, tenant_id: uuid.UUID, *, now: datetime | None = None) -> TenantSubscription:
    subscription = _load_subscription(db, tenant_id)
    if not subscription_is_usable(subscription, now=now):
        raise SubscriptionInactiveError("Subscription is not active")
    return subscription


def ai_usage_available(db: Session, tenant_id: uuid.UUID, *, now: datetime | None = None) -> int:
    """Remaining AI calls (monthly + pack) without mutating counters."""
    moment = now or utc_now()
    try:
        require_active_subscription(db, tenant_id, now=moment)
    except SubscriptionInactiveError:
        return 0
    tenant = db.get(Tenant, tenant_id)
    if tenant is None or tenant.deleted:
        return 0
    usage_period = get_current_usage_period(db, tenant_id, now=moment)
    if usage_period is None:
        return max(tenant.usage_pack_balance, 0)
    monthly_remaining = max(usage_period.monthly_limit - usage_period.monthly_used, 0)
    return monthly_remaining + max(tenant.usage_pack_balance, 0)


def _atomic_increment_monthly_used(db: Session, period_id: uuid.UUID) -> bool:
    updated_id = db.execute(
        update(TenantUsagePeriod)
        .where(
            TenantUsagePeriod.id == period_id,
            TenantUsagePeriod.deleted.is_(False),
            TenantUsagePeriod.monthly_used < TenantUsagePeriod.monthly_limit,
        )
        .values(monthly_used=TenantUsagePeriod.monthly_used + 1)
        .returning(TenantUsagePeriod.id)
    ).scalar_one_or_none()
    return updated_id is not None


def _atomic_decrement_pack_balance(db: Session, tenant_id: uuid.UUID) -> bool:
    updated_id = db.execute(
        update(Tenant)
        .where(
            Tenant.id == tenant_id,
            Tenant.deleted.is_(False),
            Tenant.usage_pack_balance > 0,
        )
        .values(usage_pack_balance=Tenant.usage_pack_balance - 1)
        .returning(Tenant.id)
    ).scalar_one_or_none()
    return updated_id is not None


def _advisory_lock_usage(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    reference_id: uuid.UUID,
    source: str,
) -> None:
    if reference_id == ZERO_UUID:
        return
    bind = db.get_bind()
    if bind.dialect.name != "postgresql":
        return
    db.execute(
        text("SELECT pg_advisory_xact_lock(hashtext(:lock_key))"),
        {"lock_key": f"{tenant_id}:{reference_id}:{source}"},
    )


def assert_ai_usage_available(db: Session, tenant_id: uuid.UUID, *, now: datetime | None = None) -> None:
    if ai_usage_available(db, tenant_id, now=now) <= 0:
        raise QuotaExceededError(dimension="ai_requests", message="AI 调用额度已用尽")


_BILLING_NS = uuid.UUID("a3b8c2e1-4f5d-4e6a-9b0c-1d2e3f4a5b6c")


def usage_reference(*parts: str) -> uuid.UUID:
    key = ":".join(str(part) for part in parts if str(part))
    return uuid.uuid5(_BILLING_NS, f"aperix-geo:{key}")


def consume_ai_usage(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    source: str,
    subject_id: uuid.UUID | None = None,
    reference_id: uuid.UUID | None = None,
    platform: str = "",
    usage: dict | None = None,
    input_tokens: int | None = None,
    output_tokens: int | None = None,
    total_tokens: int | None = None,
    now: datetime | None = None,
) -> str:
    """Atomically deduct one AI request. Returns ``subscription`` or ``pack``."""
    moment = now or utc_now()
    ref = reference_id or ZERO_UUID
    _advisory_lock_usage(db, tenant_id=tenant_id, reference_id=ref, source=source)

    existing = existing_consumption_pool(db, tenant_id=tenant_id, reference_id=ref, source=source)
    if existing is not None:
        return existing

    require_active_subscription(db, tenant_id, now=moment)

    if input_tokens is None or output_tokens is None or total_tokens is None:
        tokens = normalize_token_usage(usage)
        input_tokens = tokens.input_tokens if input_tokens is None else max(input_tokens, 0)
        output_tokens = tokens.output_tokens if output_tokens is None else max(output_tokens, 0)
        total_tokens = tokens.total_tokens if total_tokens is None else max(total_tokens, 0)
    else:
        input_tokens = max(input_tokens, 0)
        output_tokens = max(output_tokens, 0)
        total_tokens = max(total_tokens, 0)

    usage_period = get_current_usage_period(db, tenant_id, now=moment)
    if usage_period is not None:
        if _atomic_increment_monthly_used(db, usage_period.id):
            consumed_from = "subscription"
        elif _atomic_decrement_pack_balance(db, tenant_id):
            consumed_from = "pack"
        else:
            raise QuotaExceededError(dimension="ai_requests", message="AI 调用额度已用尽")
    elif _atomic_decrement_pack_balance(db, tenant_id):
        consumed_from = "pack"
    else:
        raise QuotaExceededError(dimension="ai_requests", message="AI 调用额度已用尽")

    row = record_consumption(
        db,
        tenant_id=tenant_id,
        source=source,
        consumed_from=consumed_from,
        reference_id=ref,
        subject_id=subject_id or ZERO_UUID,
        platform=platform,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total_tokens,
    )
    if row is None:
        replay = existing_consumption_pool(db, tenant_id=tenant_id, reference_id=ref, source=source)
        if replay is not None:
            return replay
        raise QuotaExceededError(dimension="ai_requests", message="AI 调用额度记录失败")
    return row.consumed_from
