import type { CtaContent } from "@/lib/home";
import type { Faq } from "@/lib/platform/faq";
import { pricingFaqDefaults as pricingFaqItemsDefaults } from "@shared/faq/defaults";
import { mergeFaqs, resolveFaqDefaults } from "@/lib/faqs";
import type { FaqDoc } from "@shared/faq";
import { backendApiBase } from "@/lib/backend";
import { appLinks } from "@/lib/app-links";

export type BillingCycle = "monthly" | "quarterly" | "yearly";

export type PlanLimitItem = {
  key: string;
  label: string;
  description: string;
  value: string;
  comparison_only?: boolean;
};

export type PlanPriceItem = {
  billing_cycle: BillingCycle;
  monthly_cents: number | null;
  period_total_cents: number | null;
  discount_badge: string | null;
};

export type PlanCatalogItem = {
  code: string;
  name: string;
  description: string;
  orderable: boolean;
  limits: PlanLimitItem[];
  prices: PlanPriceItem[];
};

export type BillingCycleOption = {
  id: BillingCycle;
  label: string;
  badge: string | null;
};

export type PlanCatalog = {
  plans: PlanCatalogItem[];
  billing_cycles: BillingCycleOption[];
};

export const pricingHero = {
  title: "定价方案",
  subtitle: "覆盖国内主流 AI 平台，实时监控分析品牌在 AI 中的竞争表现。",
};

export async function getPlanCatalog(): Promise<PlanCatalog> {
  const url = `${backendApiBase()}/billing/plans`;

  let response: Response;
  try {
    response = await fetch(url, {
      headers: { Accept: "application/json" },
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    throw new Error(`无法连接定价 API（${url}）：${message}`);
  }

  if (!response.ok) {
    throw new Error(`定价 API 返回 ${response.status}（${url}）`);
  }

  const catalog = (await response.json()) as PlanCatalog;
  if (!catalog.plans?.length) {
    throw new Error(`定价 API 未返回计划数据（${url}）`);
  }

  return catalog;
}

export const pricingComparison = {
  title: "完整功能对比",
  description: "对比所有版本的限制与能力。",
};

export function planCardLimits(plan: PlanCatalogItem): PlanLimitItem[] {
  return plan.limits.filter((limit) => !limit.comparison_only);
}

export function planComparisonRows(
  plans: PlanCatalogItem[],
): Array<{ key: string; label: string; description: string; values: string[] }> {
  if (plans.length === 0) return [];
  return plans[0].limits.map((limit) => ({
    key: limit.key,
    label: limit.label,
    description: limit.description,
    values: plans.map((plan) => plan.limits.find((item) => item.key === limit.key)?.value ?? "—"),
  }));
}

export function planDisplayPrice(plan: PlanCatalogItem, cycle: BillingCycle): string | null {
  const price = plan.prices.find((item) => item.billing_cycle === cycle);
  if (!price?.monthly_cents || price.monthly_cents <= 0) return null;
  return Math.round(price.monthly_cents / 100).toLocaleString("zh-CN");
}

export const pricingRegisterHref = appLinks.register;

export const pricingCta: CtaContent = {
  badge: "准备就绪",
  titleBefore: "准备好提升",
  titleHighlight: "AI 可见度",
  titleAfter: "了吗？",
  description: "从免费注册开始，选择适合团队的订阅方案。",
  codeLines: ["// 停止猜测。", "// 开始掌控。"],
  secondaryCtaLabel: "获取演示",
  secondaryCtaHref: pricingRegisterHref,
  primaryCtaLabel: "开始免费试用",
  primaryCtaHref: pricingRegisterHref,
};

export const pricingFaqSection = {
  title: "常见问题",
  subtitle: "购买或升级前的常见问题。",
} as const;

export const pricingFaqs: Faq[] = resolveFaqDefaults(pricingFaqItemsDefaults);

export function mergePricingFaqs(cms: FaqDoc[] | null | undefined): Faq[] {
  return mergeFaqs(cms, pricingFaqs);
}
