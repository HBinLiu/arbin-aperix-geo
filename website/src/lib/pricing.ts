import type { CtaContent } from "@/lib/home";
import type { PlatformFaqItem } from "@/lib/platform/faq";
import { backendApiBase } from "@/lib/backend";

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

export const pricingRegisterHref = "/auth/register";

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

export const pricingFaqDefaults = {
  title: "常见问题",
  subtitle: "购买或升级前的常见问题。",
} as const;

export const pricingFaqs: PlatformFaqItem[] = [
  {
    number: "01",
    label: "提示词",
    question: "提示词代表什么？",
    paragraphs: [
      "提示词是你希望 AI 回答的业务问题，例如「哪个 GEO 工具适合中小企业」或「某品类推荐哪家品牌」。",
      "如果您每天在 3 个模型上运行 50 个 Prompt，持续 30 天，那么总共会追踪 4,500 条回答。",
    ],
  },
  {
    number: "02",
    label: "品牌",
    question: "我可以把提示词分配到多个品牌中吗？",
    paragraphs: [
      "可以。每个品牌拥有独立的提示词库与监测配置，你可以在订阅额度内创建多个品牌，分别追踪不同产品线的 AI 可见性。",
      "团队席位支持多人协作，同一品牌下的提示词、竞争对手与采样结果对团队成员共享。",
    ],
  },
  {
    number: "03",
    label: "方案",
    question: "后续可以调整使用量或更换方案吗？",
    paragraphs: [
      "可以。随着使用量增长，您可以随时切换方案。企业版也支持增加自定义模型包和专属服务。",
    ],
  },
  {
    number: "04",
    label: "计费",
    question: "是否提供年付或季付折扣？",
    paragraphs: [
      "提供。年付或季付可享受额外优惠，非常适合持续开展 GEO 运营的团队。",
    ],
  },
];
