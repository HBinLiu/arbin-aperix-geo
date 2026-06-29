"""Effective plan limits with tenant overrides."""

from __future__ import annotations

from dataclasses import dataclass

from aperix_geo.db.models import Plan, TenantPlanOverride


@dataclass(frozen=True, slots=True)
class PlanLimits:
    max_subjects: int
    max_per_platforms: int
    max_per_competitors: int
    max_prompts_total: int
    per_month_usages: int
    max_team_members: int
    sampling_frequency: str


def effective_int(override_val: int, plan_val: int) -> int:
    return override_val if override_val != 0 else plan_val


def effective_str(override_val: str, plan_val: str) -> str:
    return override_val.strip() if override_val.strip() else plan_val


def effective_limits(plan: Plan, override: TenantPlanOverride | None) -> PlanLimits:
    if override is None:
        return PlanLimits(
            max_subjects=plan.max_subjects,
            max_per_platforms=plan.max_per_platforms,
            max_per_competitors=plan.max_per_competitors,
            max_prompts_total=plan.max_prompts_total,
            per_month_usages=plan.per_month_usages,
            max_team_members=plan.max_team_members,
            sampling_frequency=plan.sampling_frequency,
        )
    return PlanLimits(
        max_subjects=effective_int(override.max_subjects, plan.max_subjects),
        max_per_platforms=effective_int(override.max_per_platforms, plan.max_per_platforms),
        max_per_competitors=effective_int(override.max_per_competitors, plan.max_per_competitors),
        max_prompts_total=effective_int(override.max_prompts_total, plan.max_prompts_total),
        per_month_usages=effective_int(override.per_month_usages, plan.per_month_usages),
        max_team_members=effective_int(override.max_team_members, plan.max_team_members),
        sampling_frequency=effective_str(override.sampling_frequency, plan.sampling_frequency),
    )
