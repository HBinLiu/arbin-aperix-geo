export type BillingCycle = "monthly" | "yearly";

export type PlanId = "starter" | "growth" | "scale" | "enterprise";

export type PlanLimit = {
  label: string;
  value: string;
};

export type SubscriptionPlan = {
  id: PlanId;
  name: string;
  description: string;
  /** 月付标价；Enterprise 为 null */
  monthlyPrice: number | null;
  limits: PlanLimit[];
  cta: "current" | "select" | "contact";
};

export const YEARLY_DISCOUNT_RATE = 0.15;

export const CURRENT_PLAN_ID: PlanId = "starter";

export const SUBSCRIPTION_PLANS: SubscriptionPlan[] = [
  {
    id: "starter",
    name: "Starter",
    description: "适合个人或小团队，快速验证品牌在 AI 搜索中的可见度。",
    monthlyPrice: 79,
    cta: "current",
    limits: [
      { label: "Credits(Agents)", value: "24,000" },
      { label: "项目", value: "1" },
      { label: "提示词", value: "50" },
      { label: "平台", value: "2" },
    ],
  },
  {
    id: "growth",
    name: "Growth",
    description: "适合成长型团队，需要更多监测额度与多项目管理能力。",
    monthlyPrice: 199,
    cta: "select",
    limits: [
      { label: "Credits(Agents)", value: "60,000" },
      { label: "项目", value: "2" },
      { label: "提示词", value: "150" },
      { label: "平台", value: "2" },
    ],
  },
  {
    id: "scale",
    name: "Scale",
    description: "适合规模化运营，覆盖更多提示词、平台与并发监测需求。",
    monthlyPrice: 499,
    cta: "select",
    limits: [
      { label: "Credits(Agents)", value: "150,000" },
      { label: "项目", value: "5" },
      { label: "提示词", value: "500" },
      { label: "平台", value: "3" },
    ],
  },
  {
    id: "enterprise",
    name: "Enterprise",
    description: "适合大型组织，提供定制化额度、专属支持与私有化选项。",
    monthlyPrice: null,
    cta: "contact",
    limits: [
      { label: "Credits(Agents)", value: "自定义" },
      { label: "项目", value: "自定义" },
      { label: "提示词", value: "自定义" },
      { label: "平台", value: "自定义" },
    ],
  },
];

export function planDisplayPrice(plan: SubscriptionPlan, cycle: BillingCycle): string {
  if (plan.monthlyPrice === null) return "自定义";
  const monthly =
    cycle === "yearly"
      ? Math.round(plan.monthlyPrice * (1 - YEARLY_DISCOUNT_RATE))
      : plan.monthlyPrice;
  return `$${monthly}`;
}

export function planCycleSuffix(cycle: BillingCycle): string {
  return cycle === "yearly" ? "/月 · 按年付" : "/月";
}

export function planCardTitle(plan: SubscriptionPlan, cycle: BillingCycle): string {
  const cycleLabel = cycle === "yearly" ? "Yearly" : "Monthly";
  return `${plan.name} ${cycleLabel}`;
}
