"""Subscription plan catalog for pricing pages."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from aperix_geo.db.models import Plan, PlanPrice
from aperix_geo.services.billing.constants import (
    BILLING_CYCLES,
    CUSTOM_LIMIT_THRESHOLD,
    ENTERPRISE_PLAN_CODE,
    ORDERABLE_PLAN_CODES,
)
from aperix_geo.services.sampling.frequency import sampling_interval_days

_BILLING_CYCLE_LABELS: dict[str, str] = {
    "monthly": "月度",
    "quarterly": "季度",
    "yearly": "年度",
}

_PLAN_DESCRIPTIONS: dict[str, str] = {
    "personal": "适合个人或小团队，快速验证品牌在 AI 平台中的可见度。",
    "premium": "适合成长型团队，多品牌监测与更高 AI 额度。",
    "ultimate": "适合规模化运营，覆盖更多品牌、提示词与高并发监测。",
    "enterprise": "适合大型组织，提供定制化额度、专属支持与私有化选项。",
}

_LIMIT_SPECS: tuple[tuple[str, str, str, bool], ...] = (
    ("max_subjects", "品牌", "可创建与监测的品牌数量上限。", False),
    ("max_per_platforms", "平台", "每个品牌可监控的AI 平台数量上限。", False),
    ("max_prompts_total", "提示词", "当前团队下全部品牌的提示词总量上限。", False),
    ("max_team_members", "团队席位", "当前团队可邀请加入的成员账号数量上限。", False),
    ("max_per_competitors", "竞争对手", "每个品牌可配置的竞争对手数量上限。", False),
    ("sampling_frequency", "采样间隔", "每个品牌自动 AI 采样的时间间隔。", True),
    ("per_month_usages", "AI 配额量", "每月可用的 AI 配额数量上限，用于 AI 请求的消耗。", False),
)

_SAMPLING_FREQUENCY_LABELS: dict[str, str] = {
    "daily_1": "每天",
    "daily_3": "每3天",
    "daily_7": "每周",
}


@dataclass(frozen=True)
class PlanLimitDisplay:
    key: str
    label: str
    description: str
    value: str
    comparison_only: bool = False


@dataclass(frozen=True)
class PlanPriceDisplay:
    billing_cycle: str
    monthly_cents: int | None
    period_total_cents: int | None
    discount_badge: str | None


@dataclass(frozen=True)
class PlanCatalogItem:
    code: str
    name: str
    description: str
    orderable: bool
    limits: tuple[PlanLimitDisplay, ...]
    prices: tuple[PlanPriceDisplay, ...]


@dataclass(frozen=True)
class BillingCycleOption:
    id: str
    label: str
    badge: str | None


@dataclass(frozen=True)
class PlanCatalog:
    plans: tuple[PlanCatalogItem, ...]
    billing_cycles: tuple[BillingCycleOption, ...]


def _is_custom_plan(plan: Plan) -> bool:
    return plan.code == ENTERPRISE_PLAN_CODE


def _format_int(value: int) -> str:
    return f"{value:,}"


def _format_discount_badge(label: str) -> str | None:
    stripped = label.strip()
    if not stripped:
        return None
    if stripped.startswith("-") and stripped.endswith("%"):
        return f"省 {stripped[1:]}"
    return stripped


def _format_limit_value(plan: Plan, key: str, raw: int | str) -> str:
    if _is_custom_plan(plan):
        return "自定义"
    if key == "sampling_frequency":
        plan_days = sampling_interval_days(str(raw))
        labels = [
            label
            for code, label in _SAMPLING_FREQUENCY_LABELS.items()
            if sampling_interval_days(code) >= plan_days
        ]
        if labels:
            return " / ".join(labels)
        return _SAMPLING_FREQUENCY_LABELS.get(str(raw), str(raw))
    if key == "max_per_competitors":
        return f"最多{raw}"
    if key == "max_team_members":
        return f"最多{raw}"
    if key == "per_month_usages":
        return f"{_format_int(int(raw))} / 月"
    if isinstance(raw, int) and raw >= CUSTOM_LIMIT_THRESHOLD:
        return "自定义"
    return _format_int(int(raw)) if isinstance(raw, int) else str(raw)


def _plan_limits(plan: Plan) -> tuple[PlanLimitDisplay, ...]:
    items: list[PlanLimitDisplay] = []
    for key, label, description, comparison_only in _LIMIT_SPECS:
        raw = getattr(plan, key)
        items.append(
            PlanLimitDisplay(
                key=key,
                label=label,
                description=description,
                value=_format_limit_value(plan, key, raw),
                comparison_only=comparison_only,
            )
        )
    return tuple(items)


def _plan_prices(prices: list[PlanPrice], *, custom: bool) -> tuple[PlanPriceDisplay, ...]:
    by_cycle = {price.billing_cycle: price for price in prices}
    items: list[PlanPriceDisplay] = []
    for cycle in BILLING_CYCLES:
        price = by_cycle.get(cycle)
        if price is None:
            continue
        if custom or price.period_total_cents <= 0:
            items.append(
                PlanPriceDisplay(
                    billing_cycle=cycle,
                    monthly_cents=None,
                    period_total_cents=None,
                    discount_badge=None,
                )
            )
            continue
        items.append(
            PlanPriceDisplay(
                billing_cycle=cycle,
                monthly_cents=price.monthly_cents,
                period_total_cents=price.period_total_cents,
                discount_badge=_format_discount_badge(price.discount_label),
            )
        )
    return tuple(items)


def _billing_cycle_options(prices: list[PlanPrice]) -> tuple[BillingCycleOption, ...]:
    by_cycle = {price.billing_cycle: price for price in prices}
    items: list[BillingCycleOption] = []
    for cycle in BILLING_CYCLES:
        if cycle not in by_cycle:
            continue
        price = by_cycle[cycle]
        items.append(
            BillingCycleOption(
                id=cycle,
                label=_BILLING_CYCLE_LABELS[cycle],
                badge=_format_discount_badge(price.discount_label),
            )
        )
    return tuple(items)


def get_plan_catalog(db: Session) -> PlanCatalog:
    """Load active subscription plans with display-ready limits and prices."""
    plans = list(
        db.execute(
            select(Plan)
            .where(Plan.is_active.is_(True), Plan.deleted.is_(False))
            .options(selectinload(Plan.prices))
            .order_by(Plan.sort_order.asc(), Plan.code.asc())
        )
        .scalars()
        .all()
    )

    catalog_plans: list[PlanCatalogItem] = []
    billing_cycles: tuple[BillingCycleOption, ...] = ()

    for plan in plans:
        active_prices = [price for price in plan.prices if not price.deleted]
        custom = _is_custom_plan(plan)
        catalog_plans.append(
            PlanCatalogItem(
                code=plan.code,
                name=plan.name,
                description=_PLAN_DESCRIPTIONS.get(plan.code, ""),
                orderable=plan.code in ORDERABLE_PLAN_CODES,
                limits=_plan_limits(plan),
                prices=_plan_prices(active_prices, custom=custom),
            )
        )
        if not custom and not billing_cycles:
            billing_cycles = _billing_cycle_options(active_prices)

    if not billing_cycles:
        billing_cycles = tuple(
            BillingCycleOption(id=cycle, label=_BILLING_CYCLE_LABELS[cycle], badge=None)
            for cycle in BILLING_CYCLES
        )

    return PlanCatalog(plans=tuple(catalog_plans), billing_cycles=billing_cycles)
