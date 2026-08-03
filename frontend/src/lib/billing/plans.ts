import {
  Building2,
  CalendarClock,
  Globe,
  MessageSquareText,
  Sparkles,
  Users,
  type LucideIcon,
} from "lucide-react";

import type { BillingCycle, PlanCatalog, PlanCatalogItem } from "@/types/billing";

const BILLING_CYCLE_LABELS: Record<BillingCycle, string> = {
  monthly: "月度",
  quarterly: "季度",
  yearly: "年度",
};

export const PLAN_LIMIT_ICONS: Record<string, LucideIcon> = {
  max_subjects: Building2,
  max_per_platforms: Globe,
  max_prompts_total: MessageSquareText,
  sampling_frequency: CalendarClock,
  max_per_competitors: Users,
  per_month_usages: Sparkles,
  max_team_members: Users,
};

export function billingCycleLabel(cycle: BillingCycle): string {
  return BILLING_CYCLE_LABELS[cycle] ?? cycle;
}

export function planDisplayPrice(plan: PlanCatalogItem, cycle: BillingCycle): string | null {
  const price = plan.prices.find((item) => item.billing_cycle === cycle);
  if (!price?.monthly_cents || price.monthly_cents <= 0) return null;
  const monthlyYuan = Math.round(price.monthly_cents / 100);
  return monthlyYuan.toLocaleString("zh-CN");
}

export function planCardLimits(plan: PlanCatalogItem): PlanCatalogItem["limits"] {
  return plan.limits.filter((limit) => !limit.comparison_only);
}

export function planComparisonRows(
  plans: PlanCatalogItem[],
): { key: string; label: string; description: string; values: string[] }[] {
  if (plans.length === 0) return [];
  return plans[0].limits.map((limit) => ({
    key: limit.key,
    label: limit.label,
    description: limit.description,
    values: plans.map((plan) => plan.limits.find((item) => item.key === limit.key)?.value ?? "—"),
  }));
}

export function resolvePlanCta(
  plan: PlanCatalogItem,
  currentPlanCode: string | null,
  currentBillingCycle: BillingCycle | null,
  selectedCycle: BillingCycle,
  options?: { subscriptionActive?: boolean },
): "current" | "select" | "contact" {
  if (!plan.orderable) return "contact";
  const subscriptionActive = options?.subscriptionActive ?? true;
  // 到期后需可续订同一计划，不能再锁成「当前订阅」
  if (
    subscriptionActive &&
    currentPlanCode &&
    currentBillingCycle &&
    plan.code === currentPlanCode &&
    selectedCycle === currentBillingCycle
  ) {
    return "current";
  }
  return "select";
}

/** Catalog is ordered by sort_order; use index to compare tiers. */
export type PlanChangeKind = "upgrade" | "downgrade" | "renewal" | "new";

export function resolvePlanChangeKind(
  plans: PlanCatalogItem[],
  currentPlanCode: string | null,
  targetPlanCode: string,
  options?: { subscriptionActive?: boolean },
): PlanChangeKind {
  if (!options?.subscriptionActive || !currentPlanCode) return "new";
  if (currentPlanCode === targetPlanCode) return "renewal";
  const currentIndex = plans.findIndex((item) => item.code === currentPlanCode);
  const targetIndex = plans.findIndex((item) => item.code === targetPlanCode);
  if (currentIndex < 0 || targetIndex < 0) return "new";
  if (targetIndex > currentIndex) return "upgrade";
  if (targetIndex < currentIndex) return "downgrade";
  return "renewal";
}

export function planSelectLabel(
  kind: PlanChangeKind,
  options?: { matchingExpired?: boolean },
): string {
  if (options?.matchingExpired) return "立即续订";
  switch (kind) {
    case "upgrade":
    case "downgrade":
    case "renewal":
      // 有效订阅下：换档位或同档换周期，统一「更换计划」
      return "更换计划";
    default:
      return "立即订阅";
  }
}

export type PlanChangeConfirmCopy = {
  title: string;
  points: string[];
  confirmLabel: string;
};

export function planChangeConfirmCopy(input: {
  kind: "upgrade" | "downgrade";
  targetPlanName: string;
  currentPlanName: string;
  periodEndLabel: string;
}): PlanChangeConfirmCopy {
  if (input.kind === "upgrade") {
    return {
      title: `确认升级到${input.targetPlanName}？`,
      points: [
        `按${input.targetPlanName}价格全额支付，不退还当前计划剩余费用。`,
        "支付成功后立即升级：额度上限按新版本生效，本周期已用次数保留。",
        "当前账期将按本次购买的计费周期顺延。",
      ],
      confirmLabel: "确认升级",
    };
  }
  return {
    title: `确认降级到${input.targetPlanName}？`,
    points: [
      `按${input.targetPlanName}价格全额支付。`,
      `支付后当期仍使用${input.currentPlanName}至 ${input.periodEndLabel}。`,
      `${input.targetPlanName}将在账期结束后生效。`,
    ],
    confirmLabel: "确认降级",
  };
}

export function planChangePayDescription(kind: PlanChangeKind): string {
  switch (kind) {
    case "upgrade":
      return "请使用微信扫一扫完成支付。支付成功后将立即升级，额度上限按新版本生效。";
    case "downgrade":
      return "请使用微信扫一扫完成支付。支付后当期仍使用当前版本，新版本在账期结束后生效。";
    case "renewal":
      return "请使用微信扫一扫完成续订支付，支付成功后账期将顺延。";
    default:
      return "请使用微信扫一扫完成订阅支付，支付成功后计划将立即生效。";
  }
}

/** 是否为租户上一次/当前绑定的计划与账期（含已到期）。 */
export function isMatchingSubscriptionPlan(
  plan: PlanCatalogItem,
  currentPlanCode: string | null,
  currentBillingCycle: BillingCycle | null,
  selectedCycle: BillingCycle,
): boolean {
  return Boolean(
    currentPlanCode &&
      currentBillingCycle &&
      plan.code === currentPlanCode &&
      selectedCycle === currentBillingCycle,
  );
}

export type { BillingCycle, PlanCatalog, PlanCatalogItem };
