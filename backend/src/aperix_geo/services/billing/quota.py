"""Tenant subscription limits and AI request quota."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import delete, func, select, text, update
from sqlalchemy.orm import Session

from aperix_geo.db.models import (
    EPOCH,
    LLMResponse,
    Plan,
    Prompt,
    SamplingJob,
    Subject,
    Tenant,
    TenantPlanOverride,
    TenantSubscription,
    TenantUsagePeriod,
    User,
    ZERO_UUID,
)
from aperix_geo.services.billing.constants import SETUP_PENDING_AI_SOFT_CAP
from aperix_geo.services.billing.exceptions import QuotaExceededError, SubscriptionInactiveError
from aperix_geo.services.billing.limits import PlanLimits, effective_limits
from aperix_geo.services.billing.quota_ledger import (
    count_pending_setup_usage,
    existing_consumption_pool,
    existing_pending_setup_usage,
    list_pending_setup_usage,
    record_consumption,
    record_pending_setup_usage,
)
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


def _find_subscription(db: Session, tenant_id: uuid.UUID) -> TenantSubscription | None:
    return db.execute(
        select(TenantSubscription)
        .where(
            TenantSubscription.tenant_id == tenant_id,
            TenantSubscription.deleted.is_(False),
        )
        .limit(1)
    ).scalar_one_or_none()


def _load_subscription(db: Session, tenant_id: uuid.UUID) -> TenantSubscription:
    subscription = _find_subscription(db, tenant_id)
    if subscription is None:
        raise SubscriptionInactiveError("Subscription not found")
    return subscription


def _load_plan_override(db: Session, tenant_id: uuid.UUID) -> TenantPlanOverride | None:
    return db.execute(
        select(TenantPlanOverride)
        .where(
            TenantPlanOverride.tenant_id == tenant_id,
            TenantPlanOverride.deleted.is_(False),
        )
        .limit(1)
    ).scalar_one_or_none()


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

    return tenant, subscription, plan, _load_plan_override(db, tenant_id)


def tenant_has_usable_subscription(
    db: Session, tenant_id: uuid.UUID, *, now: datetime | None = None
) -> bool:
    subscription = _find_subscription(db, tenant_id)
    return subscription is not None and subscription_is_usable(subscription, now=now)


def is_first_subject_onboarding(
    db: Session, tenant_id: uuid.UUID, *, now: datetime | None = None
) -> bool:
    """True when the tenant may run first-brand setup without an active subscription."""
    return _count_subjects(db, tenant_id) == 0 and not tenant_has_usable_subscription(
        db, tenant_id, now=now
    )


def personal_plan_limits(db: Session) -> PlanLimits:
    plan = db.execute(
        select(Plan).where(
            Plan.code == "personal",
            Plan.is_active.is_(True),
            Plan.deleted.is_(False),
        ).limit(1)
    ).scalar_one_or_none()
    if plan is None:
        raise SubscriptionInactiveError("Personal plan not found")
    return effective_limits(plan, None)


def get_limits_for_enforcement(db: Session, tenant_id: uuid.UUID) -> PlanLimits:
    """Limits for capacity checks: active plan, or personal during first-subject onboarding."""
    if tenant_has_usable_subscription(db, tenant_id):
        return get_limits_for_tenant(db, tenant_id)
    if is_first_subject_onboarding(db, tenant_id):
        return personal_plan_limits(db)
    raise SubscriptionInactiveError("Subscription is not active")


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


def _monthly_free(usage_period: TenantUsagePeriod) -> int:
    return max(
        usage_period.monthly_limit - usage_period.monthly_used - usage_period.monthly_reserved,
        0,
    )


def _pack_free(tenant: Tenant) -> int:
    return max(tenant.usage_pack_balance - tenant.usage_pack_reserved, 0)


def _build_usage_snapshot(
    db: Session,
    tenant: Tenant,
    limits: PlanLimits,
    usage_period: TenantUsagePeriod | None,
) -> UsageSnapshot:
    monthly_limit = usage_period.monthly_limit if usage_period is not None else limits.per_month_usages
    monthly_used = usage_period.monthly_used if usage_period is not None else 0
    monthly_remaining = _monthly_free(usage_period) if usage_period is not None else 0
    pack_balance = tenant.usage_pack_balance
    pack_free = _pack_free(tenant)
    return UsageSnapshot(
        subjects_count=_count_subjects(db, tenant.id),
        prompts_count=_count_prompts(db, tenant.id),
        monthly_limit=monthly_limit,
        monthly_used=monthly_used,
        monthly_remaining=monthly_remaining,
        usage_pack_balance=pack_balance,
        ai_requests_available=monthly_remaining + pack_free,
    )


def get_subscription_snapshot(db: Session, tenant_id: uuid.UUID, *, now: datetime | None = None) -> SubscriptionSnapshot:
    moment = now or utc_now()
    tenant = db.get(Tenant, tenant_id)
    if tenant is None or tenant.deleted:
        raise SubscriptionInactiveError("Tenant not found")

    subscription = _find_subscription(db, tenant_id)
    if subscription is None:
        limits = personal_plan_limits(db)
        plan = db.execute(
            select(Plan).where(Plan.code == "personal", Plan.deleted.is_(False)).limit(1)
        ).scalar_one()
        return SubscriptionSnapshot(
            plan_code=plan.code,
            plan_name=plan.name,
            billing_cycle="monthly",
            status="expired",
            current_period_start=EPOCH,
            current_period_end=EPOCH,
            ai_period_start=None,
            ai_period_end=None,
            subscription_active=False,
            limits=limits,
            usage=_build_usage_snapshot(db, tenant, limits, None),
        )

    plan = db.get(Plan, subscription.plan_id)
    if plan is None or plan.deleted:
        raise SubscriptionInactiveError("Plan not found")
    override = _load_plan_override(db, tenant_id)
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


def _require_subscription_unless_onboarding(
    db: Session, tenant_id: uuid.UUID, *, now: datetime | None = None
) -> None:
    if not is_first_subject_onboarding(db, tenant_id, now=now):
        require_active_subscription(db, tenant_id, now=now)


def assert_can_create_subject(db: Session, tenant_id: uuid.UUID) -> None:
    _require_subscription_unless_onboarding(db, tenant_id)
    limits = get_limits_for_enforcement(db, tenant_id)
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
    _require_subscription_unless_onboarding(db, tenant_id)
    limits = get_limits_for_enforcement(db, tenant_id)
    if _active_competitor_count(subject) + adding > limits.max_per_competitors:
        raise QuotaExceededError(
            dimension="max_per_competitors",
            message=f"竞争对手已达上限（{limits.max_per_competitors} 个）",
        )


def assert_platform_capacity(db: Session, tenant_id: uuid.UUID, platform_count: int) -> None:
    _require_subscription_unless_onboarding(db, tenant_id)
    limits = get_limits_for_enforcement(db, tenant_id)
    if platform_count > limits.max_per_platforms:
        raise QuotaExceededError(
            dimension="max_per_platforms",
            message=f"平台数量超过上限（{limits.max_per_platforms} 个）",
        )


def remaining_prompt_slots(db: Session, tenant_id: uuid.UUID) -> int:
    limits = get_limits_for_enforcement(db, tenant_id)
    used = _count_prompts(db, tenant_id)
    return max(0, limits.max_prompts_total - used)


def assert_can_add_prompts(db: Session, tenant_id: uuid.UUID, *, count: int) -> None:
    _require_subscription_unless_onboarding(db, tenant_id)
    remaining = remaining_prompt_slots(db, tenant_id)
    if count <= remaining:
        return
    limits = get_limits_for_enforcement(db, tenant_id)
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
    """Remaining AI calls (monthly + pack - reserved) without mutating counters."""
    moment = now or utc_now()
    try:
        require_active_subscription(db, tenant_id, now=moment)
    except SubscriptionInactiveError:
        return 0
    tenant = db.get(Tenant, tenant_id)
    if tenant is None or tenant.deleted:
        return 0
    usage_period = get_current_usage_period(db, tenant_id, now=moment)
    pack_free = _pack_free(tenant)
    if usage_period is None:
        return pack_free
    return _monthly_free(usage_period) + pack_free


def lock_tenant_ai_quota(db: Session, tenant_id: uuid.UUID, *, now: datetime | None = None) -> int:
    """Acquire tenant AI quota locks for this transaction and return available calls.

    Intended for create-sampling: hold locks through truncation + ``reserve_ai_usage``
    so concurrent creators cannot oversubscribe. Read-only callers should use
    ``ai_usage_available`` instead.
    """
    moment = now or utc_now()
    try:
        require_active_subscription(db, tenant_id, now=moment)
    except SubscriptionInactiveError:
        return 0

    _advisory_lock_tenant_quota(db, tenant_id)
    tenant = db.execute(select(Tenant).where(Tenant.id == tenant_id).with_for_update()).scalar_one_or_none()
    if tenant is None or tenant.deleted:
        return 0

    usage_period = get_current_usage_period(db, tenant_id, now=moment)
    if usage_period is not None:
        usage_period = db.execute(
            select(TenantUsagePeriod).where(TenantUsagePeriod.id == usage_period.id).with_for_update()
        ).scalar_one()
        return _monthly_free(usage_period) + _pack_free(tenant)
    return _pack_free(tenant)


def _atomic_increment_monthly_used(db: Session, period_id: uuid.UUID) -> bool:
    updated_id = db.execute(
        update(TenantUsagePeriod)
        .where(
            TenantUsagePeriod.id == period_id,
            TenantUsagePeriod.deleted.is_(False),
            TenantUsagePeriod.monthly_used + TenantUsagePeriod.monthly_reserved
            < TenantUsagePeriod.monthly_limit,
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
            Tenant.usage_pack_balance > Tenant.usage_pack_reserved,
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


def _advisory_lock_tenant_quota(db: Session, tenant_id: uuid.UUID) -> None:
    bind = db.get_bind()
    if bind.dialect.name != "postgresql":
        return
    db.execute(
        text("SELECT pg_advisory_xact_lock(hashtext(:lock_key))"),
        {"lock_key": f"tenant-quota:{tenant_id}"},
    )


def reserve_ai_usage(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    amount: int,
    job: SamplingJob,
    now: datetime | None = None,
) -> None:
    """Freeze ``amount`` AI calls for a sampling job (monthly first, then pack)."""
    if amount <= 0:
        return
    moment = now or utc_now()
    require_active_subscription(db, tenant_id, now=moment)
    _advisory_lock_tenant_quota(db, tenant_id)

    tenant = db.execute(select(Tenant).where(Tenant.id == tenant_id).with_for_update()).scalar_one_or_none()
    if tenant is None or tenant.deleted:
        raise QuotaExceededError(dimension="ai_requests", message="AI 调用额度不足，无法开始采样")

    usage_period = get_current_usage_period(db, tenant_id, now=moment)
    if usage_period is not None:
        usage_period = db.execute(
            select(TenantUsagePeriod).where(TenantUsagePeriod.id == usage_period.id).with_for_update()
        ).scalar_one()

    monthly_free = _monthly_free(usage_period) if usage_period is not None else 0
    pack_free = _pack_free(tenant)
    if monthly_free + pack_free < amount:
        raise QuotaExceededError(dimension="ai_requests", message="AI 调用额度不足，无法开始采样")

    take_monthly = min(amount, monthly_free)
    take_pack = amount - take_monthly
    if usage_period is not None and take_monthly:
        usage_period.monthly_reserved += take_monthly
    if take_pack:
        tenant.usage_pack_reserved += take_pack

    # Additive so retries can top up an existing job after prior releases.
    prior_open_monthly = int(job.quota_open_monthly or 0)
    prior_open_pack = int(job.quota_open_pack or 0)
    if (
        take_monthly
        and prior_open_monthly > 0
        and usage_period is not None
        and job.quota_usage_period_id not in (ZERO_UUID, usage_period.id)
    ):
        raise QuotaExceededError(
            dimension="ai_requests",
            message="采样预留账期冲突，请待当前任务结束后再重试",
        )
    if take_monthly:
        job.quota_reserved_monthly = int(job.quota_reserved_monthly or 0) + take_monthly
        job.quota_open_monthly = prior_open_monthly + take_monthly
    if take_pack:
        job.quota_reserved_pack = int(job.quota_reserved_pack or 0) + take_pack
        job.quota_open_pack = prior_open_pack + take_pack
    if prior_open_monthly == 0 and prior_open_pack == 0:
        job.quota_usage_period_id = usage_period.id if usage_period is not None else ZERO_UUID
    elif take_monthly and prior_open_monthly == 0:
        job.quota_usage_period_id = usage_period.id if usage_period is not None else ZERO_UUID


def _locked_job_usage_period(db: Session, job: SamplingJob) -> TenantUsagePeriod | None:
    """Load the usage period that holds this job's monthly reservation (not necessarily current)."""
    if job.quota_usage_period_id == ZERO_UUID:
        return None
    return db.execute(
        select(TenantUsagePeriod)
        .where(
            TenantUsagePeriod.id == job.quota_usage_period_id,
            TenantUsagePeriod.deleted.is_(False),
        )
        .with_for_update()
    ).scalar_one_or_none()


def _pop_open_pool(job: SamplingJob) -> str:
    """Take one open reservation from the job; returns ``subscription`` or ``pack``."""
    if job.quota_open_monthly > 0:
        job.quota_open_monthly -= 1
        return "subscription"
    if job.quota_open_pack > 0:
        job.quota_open_pack -= 1
        return "pack"
    raise QuotaExceededError(dimension="ai_requests", message="采样预留额度已用尽")


def confirm_sampling_quota(
    db: Session,
    *,
    job: SamplingJob,
    row: LLMResponse,
    subject_id: uuid.UUID | None = None,
    platform: str = "",
    usage: dict | None = None,
    now: datetime | None = None,
) -> str:
    """Convert one reserved call into a real consumption for a successful LLM sample."""
    if row.quota_settled:
        existing = existing_consumption_pool(
            db, tenant_id=job.tenant_id, reference_id=row.id, source="sampling"
        )
        return existing or ""

    _advisory_lock_tenant_quota(db, job.tenant_id)
    locked_job = db.execute(
        select(SamplingJob).where(SamplingJob.id == job.id).with_for_update()
    ).scalar_one()
    if row.quota_settled:
        existing = existing_consumption_pool(
            db, tenant_id=locked_job.tenant_id, reference_id=row.id, source="sampling"
        )
        return existing or ""

    existing = existing_consumption_pool(
        db, tenant_id=locked_job.tenant_id, reference_id=row.id, source="sampling"
    )
    if existing is not None:
        row.quota_settled = True
        return existing

    pool = _pop_open_pool(locked_job)
    tenant = db.execute(
        select(Tenant).where(Tenant.id == locked_job.tenant_id).with_for_update()
    ).scalar_one()
    if pool == "subscription":
        usage_period = _locked_job_usage_period(db, locked_job)
        if usage_period is None or usage_period.monthly_reserved <= 0:
            raise QuotaExceededError(dimension="ai_requests", message="采样预留额度已用尽")
        usage_period.monthly_reserved -= 1
        usage_period.monthly_used += 1
        consumed_from = "subscription"
    else:
        if tenant.usage_pack_reserved <= 0 or tenant.usage_pack_balance <= 0:
            raise QuotaExceededError(dimension="ai_requests", message="采样预留额度已用尽")
        tenant.usage_pack_reserved -= 1
        tenant.usage_pack_balance -= 1
        consumed_from = "pack"

    tokens = normalize_token_usage(usage)
    ledger = record_consumption(
        db,
        tenant_id=locked_job.tenant_id,
        source="sampling",
        consumed_from=consumed_from,
        reference_id=row.id,
        subject_id=subject_id or locked_job.subject_id,
        platform=platform or row.platform,
        input_tokens=tokens.input_tokens,
        output_tokens=tokens.output_tokens,
        total_tokens=tokens.total_tokens,
    )
    if ledger is None:
        replay = existing_consumption_pool(
            db, tenant_id=locked_job.tenant_id, reference_id=row.id, source="sampling"
        )
        if replay is None:
            raise QuotaExceededError(dimension="ai_requests", message="AI 调用额度记录失败")
        consumed_from = replay
    row.quota_settled = True
    # Keep caller's job object in sync when it is a different instance.
    job.quota_open_monthly = locked_job.quota_open_monthly
    job.quota_open_pack = locked_job.quota_open_pack
    return consumed_from


def release_sampling_quota(db: Session, *, job: SamplingJob, row: LLMResponse) -> None:
    """Release one reserved call when a response will not consume AI."""
    if row.quota_settled:
        return
    _advisory_lock_tenant_quota(db, job.tenant_id)
    locked_job = db.execute(
        select(SamplingJob).where(SamplingJob.id == job.id).with_for_update()
    ).scalar_one()
    if row.quota_settled:
        return
    if locked_job.quota_open_monthly + locked_job.quota_open_pack <= 0:
        row.quota_settled = True
        return

    pool = _pop_open_pool(locked_job)
    tenant = db.execute(
        select(Tenant).where(Tenant.id == locked_job.tenant_id).with_for_update()
    ).scalar_one()
    if pool == "subscription":
        usage_period = _locked_job_usage_period(db, locked_job)
        if usage_period is not None and usage_period.monthly_reserved > 0:
            usage_period.monthly_reserved -= 1
    elif tenant.usage_pack_reserved > 0:
        tenant.usage_pack_reserved -= 1

    row.quota_settled = True
    job.quota_open_monthly = locked_job.quota_open_monthly
    job.quota_open_pack = locked_job.quota_open_pack


def release_remaining_job_quota(db: Session, *, job: SamplingJob) -> int:
    """Release any open reservations left on a terminal sampling job."""
    open_total = job.quota_open_monthly + job.quota_open_pack
    if open_total <= 0:
        return 0
    _advisory_lock_tenant_quota(db, job.tenant_id)
    locked_job = db.execute(
        select(SamplingJob).where(SamplingJob.id == job.id).with_for_update()
    ).scalar_one()
    release_monthly = locked_job.quota_open_monthly
    release_pack = locked_job.quota_open_pack
    if release_monthly + release_pack <= 0:
        return 0

    tenant = db.execute(
        select(Tenant).where(Tenant.id == locked_job.tenant_id).with_for_update()
    ).scalar_one()
    if release_monthly:
        usage_period = _locked_job_usage_period(db, locked_job)
        if usage_period is not None:
            usage_period.monthly_reserved = max(usage_period.monthly_reserved - release_monthly, 0)
    if release_pack:
        tenant.usage_pack_reserved = max(tenant.usage_pack_reserved - release_pack, 0)

    locked_job.quota_open_monthly = 0
    locked_job.quota_open_pack = 0
    job.quota_open_monthly = 0
    job.quota_open_pack = 0
    return release_monthly + release_pack


def delete_sampling_jobs_releasing_quota(db: Session, job_ids: list[uuid.UUID]) -> int:
    """Release open reservations then delete sampling jobs. Returns deleted row count."""
    if not job_ids:
        return 0

    for job_id in job_ids:
        job = db.execute(
            select(SamplingJob).where(SamplingJob.id == job_id).with_for_update()
        ).scalar_one_or_none()
        if job is not None:
            release_remaining_job_quota(db, job=job)
    result = db.execute(delete(SamplingJob).where(SamplingJob.id.in_(job_ids)))
    return int(result.rowcount or 0)


def assert_ai_usage_available(db: Session, tenant_id: uuid.UUID, *, now: datetime | None = None) -> None:
    moment = now or utc_now()
    require_active_subscription(db, tenant_id, now=moment)
    # Read remaining directly — do not call ai_usage_available (re-checks subscription and
    # can race-map a just-expired tenant to QuotaExceededError).
    tenant = db.get(Tenant, tenant_id)
    if tenant is None or tenant.deleted:
        raise SubscriptionInactiveError("Tenant not found")
    usage_period = get_current_usage_period(db, tenant_id, now=moment)
    remaining = _pack_free(tenant)
    if usage_period is not None:
        remaining += _monthly_free(usage_period)
    if remaining <= 0:
        raise QuotaExceededError(dimension="ai_requests", message="AI 调用额度已用尽")


def assert_setup_ai_usage_available(
    db: Session, tenant_id: uuid.UUID, *, now: datetime | None = None
) -> None:
    """Gate setup AI: active subscription quota, or pending soft-cap during onboarding."""
    moment = now or utc_now()
    if tenant_has_usable_subscription(db, tenant_id, now=moment):
        assert_ai_usage_available(db, tenant_id, now=moment)
        return
    if not is_first_subject_onboarding(db, tenant_id, now=moment):
        raise SubscriptionInactiveError("Subscription is not active")
    if count_pending_setup_usage(db, tenant_id) >= SETUP_PENDING_AI_SOFT_CAP:
        raise QuotaExceededError(
            dimension="ai_requests",
            message=f"设置向导 AI 调用已达上限（{SETUP_PENDING_AI_SOFT_CAP} 次），请先完成订阅",
        )


def charge_setup_ai_usage(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    reference_id: uuid.UUID,
    platform: str = "",
    usage: dict | None = None,
    now: datetime | None = None,
) -> str:
    """Consume immediately when subscribed; otherwise defer as pending_setup during onboarding."""
    moment = now or utc_now()
    if tenant_has_usable_subscription(db, tenant_id, now=moment):
        return consume_ai_usage(
            db,
            tenant_id=tenant_id,
            source="setup",
            reference_id=reference_id,
            platform=platform,
            usage=usage,
            now=moment,
        )
    if not is_first_subject_onboarding(db, tenant_id, now=moment):
        raise SubscriptionInactiveError("Subscription is not active")

    tokens = normalize_token_usage(usage)
    already = existing_pending_setup_usage(
        db, tenant_id=tenant_id, reference_id=reference_id, source="setup"
    )
    if already is None and count_pending_setup_usage(db, tenant_id) >= SETUP_PENDING_AI_SOFT_CAP:
        raise QuotaExceededError(
            dimension="ai_requests",
            message=f"设置向导 AI 调用已达上限（{SETUP_PENDING_AI_SOFT_CAP} 次），请先完成订阅",
        )
    record_pending_setup_usage(
        db,
        tenant_id=tenant_id,
        reference_id=reference_id,
        source="setup",
        platform=platform,
        input_tokens=tokens.input_tokens,
        output_tokens=tokens.output_tokens,
        total_tokens=tokens.total_tokens,
    )
    return "pending"


def settle_pending_setup_usage(db: Session, tenant_id: uuid.UUID, *, now: datetime | None = None) -> int:
    """Convert deferred setup AI rows into real consumptions. Returns settled count."""
    moment = now or utc_now()
    require_active_subscription(db, tenant_id, now=moment)
    pending = list_pending_setup_usage(db, tenant_id)
    settled = 0
    for row in pending:
        consume_ai_usage(
            db,
            tenant_id=tenant_id,
            source=row.source or "setup",
            reference_id=row.reference_id,
            platform=row.platform,
            input_tokens=row.input_tokens,
            output_tokens=row.output_tokens,
            total_tokens=row.total_tokens,
            now=moment,
        )
        row.soft_delete()
        settled += 1
    return settled


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
