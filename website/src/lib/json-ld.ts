import type { FaqItem } from "@/lib/home";
import type { PlatformFaqItem } from "@/lib/platform/faq";
import {
  planCardLimits,
  type BillingCycle,
  type PlanCatalog,
  type PlanCatalogItem,
  type PlanPriceItem,
} from "@/lib/pricing";
import { pricingSeo } from "@/lib/seo";
import { siteConfig } from "@site";

function toAbsoluteUrl(site: URL, pathOrUrl: string): string {
  if (pathOrUrl.startsWith("http://") || pathOrUrl.startsWith("https://")) {
    return pathOrUrl;
  }
  return new URL(pathOrUrl, site).href;
}

/** schema.org Organization */
export function buildOrganizationJsonLd(site: URL) {
  return {
    "@context": "https://schema.org",
    "@type": "Organization",
    name: siteConfig.name,
    url: toAbsoluteUrl(site, "/"),
    logo: toAbsoluteUrl(site, siteConfig.logo),
    description: siteConfig.description,
  };
}

function platformFaqAnswerText(item: PlatformFaqItem): string {
  const parts = [...item.paragraphs];
  if (item.bullets?.length) {
    parts.push(...item.bullets.map((bullet) => `• ${bullet}`));
  }
  if (item.closingParagraphs?.length) {
    parts.push(...item.closingParagraphs);
  }
  return parts.join("\n\n");
}

/** PlatformFaqItem → FAQPage 可用的 question/answer */
export function platformFaqsToFaqItems(items: PlatformFaqItem[]): FaqItem[] {
  return items.map((item) => ({
    question: item.question,
    answer: platformFaqAnswerText(item),
  }));
}

/** schema.org FAQPage */
export function buildFaqPageJsonLd(faqs: FaqItem[]) {
  return {
    "@context": "https://schema.org",
    "@type": "FAQPage",
    mainEntity: faqs.map((faq) => ({
      "@type": "Question",
      name: faq.question,
      acceptedAnswer: {
        "@type": "Answer",
        text: faq.answer,
      },
    })),
  };
}

/** 首页：Organization + FAQPage */
export function buildHomeJsonLd(site: URL, faqs: FaqItem[]) {
  return [buildOrganizationJsonLd(site), buildFaqPageJsonLd(faqs)];
}

/** 平台功能页：FAQPage（PlatformFaqItem 含多段落/列表） */
export function buildPlatformFaqJsonLd(items: PlatformFaqItem[]) {
  return buildFaqPageJsonLd(platformFaqsToFaqItems(items));
}

const BILLING_CYCLE_DURATION: Record<BillingCycle, string> = {
  monthly: "P1M",
  quarterly: "P3M",
  yearly: "P1Y",
};

function formatCny(cents: number): string {
  return Math.round(cents / 100).toLocaleString("zh-CN");
}

function planLimitsText(plan: PlanCatalogItem): string {
  const limits = planCardLimits(plan);
  if (limits.length === 0) return "";
  return limits.map((limit) => `${limit.label} ${limit.value}`).join("；");
}

function planAllPricesText(plan: PlanCatalogItem, catalog: PlanCatalog): string {
  return catalog.billing_cycles
    .map((cycle) => {
      const price = plan.prices.find((item) => item.billing_cycle === cycle.id);
      if (!price?.monthly_cents || price.monthly_cents <= 0) return null;
      const monthly = `¥${formatCny(price.monthly_cents)}/月`;
      const badge = price.discount_badge ? `（${price.discount_badge}）` : "";
      const period =
        cycle.id !== "monthly" && price.period_total_cents
          ? `，账期 ¥${formatCny(price.period_total_cents)}`
          : "";
      return `${cycle.label} ${monthly}${badge}${period}`;
    })
    .filter((line): line is string => line !== null)
    .join("；");
}

function planOfferDescription(plan: PlanCatalogItem, catalog: PlanCatalog): string {
  const parts = [plan.description];
  const limits = planLimitsText(plan);
  const prices = planAllPricesText(plan, catalog);
  if (limits) parts.push(`额度：${limits}`);
  if (prices) parts.push(`价格：${prices}`);
  return parts.join("\n");
}

function offerPriceFields(price: PlanPriceItem, cycle: BillingCycle, cycleLabel: string) {
  const monthlyYuan = price.monthly_cents! / 100;
  if (cycle === "monthly") {
    return {
      price: String(monthlyYuan),
      priceSpecification: {
        "@type": "UnitPriceSpecification",
        price: String(monthlyYuan),
        priceCurrency: "CNY",
        billingDuration: BILLING_CYCLE_DURATION[cycle],
        unitText: cycleLabel,
      },
    };
  }

  const periodYuan = (price.period_total_cents ?? 0) / 100;
  return {
    price: String(periodYuan),
    priceSpecification: {
      "@type": "UnitPriceSpecification",
      price: String(periodYuan),
      priceCurrency: "CNY",
      billingDuration: BILLING_CYCLE_DURATION[cycle],
      unitText: cycleLabel,
      description: `折合 ¥${formatCny(price.monthly_cents!)}/月`,
    },
  };
}

function buildPlanOffer(
  site: URL,
  plan: PlanCatalogItem,
  catalog: PlanCatalog,
  cycle: BillingCycle,
) {
  const price = plan.prices.find((item) => item.billing_cycle === cycle);
  if (!price?.monthly_cents || price.monthly_cents <= 0) return null;

  const cycleLabel =
    catalog.billing_cycles.find((item) => item.id === cycle)?.label ?? cycle;
  const priceFields = offerPriceFields(price, cycle, cycleLabel);

  return {
    "@type": "Offer",
    name: `${plan.name}（${cycleLabel}）`,
    description: planOfferDescription(plan, catalog),
    ...priceFields,
    priceCurrency: "CNY",
    url: toAbsoluteUrl(site, "/pricing/"),
    availability: "https://schema.org/InStock",
  };
}

/** 定价页：Product + 各套餐 × 付款周期 Offer（含额度与全周期价格说明） */
export function buildPricingJsonLd(site: URL, catalog: PlanCatalog) {
  const cycles = catalog.billing_cycles.map((cycle) => cycle.id);
  const offers = catalog.plans
    .filter((plan) => plan.orderable)
    .flatMap((plan) =>
      cycles
        .map((cycle) => buildPlanOffer(site, plan, catalog, cycle))
        .filter((offer): offer is NonNullable<typeof offer> => offer !== null),
    );

  return {
    "@context": "https://schema.org",
    "@type": "Product",
    name: `${siteConfig.name} 订阅方案`,
    description: pricingSeo.description,
    brand: {
      "@type": "Brand",
      name: siteConfig.name,
    },
    offers: offers.length === 1 ? offers[0] : offers,
  };
}
