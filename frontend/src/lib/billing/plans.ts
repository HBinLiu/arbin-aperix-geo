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
): "current" | "select" | "contact" {
  if (!plan.orderable) return "contact";
  if (
    currentPlanCode &&
    currentBillingCycle &&
    plan.code === currentPlanCode &&
    selectedCycle === currentBillingCycle
  ) {
    return "current";
  }
  return "select";
}

export type { BillingCycle, PlanCatalog, PlanCatalogItem };
