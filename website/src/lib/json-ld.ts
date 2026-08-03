import type { Faq } from "@/lib/faqs";
import { faqAnswerText } from "@/lib/faqs";
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

/** schema.org WebSite */
export function buildWebSiteJsonLd(site: URL) {
  return {
    "@context": "https://schema.org",
    "@type": "WebSite",
    name: siteConfig.name,
    url: toAbsoluteUrl(site, "/"),
    description: siteConfig.description,
    publisher: {
      "@type": "Organization",
      name: siteConfig.name,
      logo: toAbsoluteUrl(site, siteConfig.logo),
    },
  };
}

/** schema.org BreadcrumbList */
export function buildBreadcrumbJsonLd(
  site: URL,
  items: Array<{ name: string; path: string }>,
) {
  return {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    itemListElement: items.map((item, index) => ({
      "@type": "ListItem",
      position: index + 1,
      name: item.name,
      item: toAbsoluteUrl(site, item.path),
    })),
  };
}

export type ArticleJsonLdInput = {
  type?: "Article" | "BlogPosting" | "NewsArticle" | "TechArticle";
  title: string;
  description: string;
  path: string;
  image?: string;
  datePublished?: string;
  dateModified?: string;
  authorName?: string;
  authorUrl?: string;
  section?: string;
};

/** schema.org Article / BlogPosting / NewsArticle */
export function buildArticleJsonLd(site: URL, input: ArticleJsonLdInput) {
  const url = toAbsoluteUrl(site, input.path);
  const image = input.image ? toAbsoluteUrl(site, input.image) : toAbsoluteUrl(site, siteConfig.ogImage);

  return {
    "@context": "https://schema.org",
    "@type": input.type ?? "Article",
    headline: input.title,
    description: input.description,
    url,
    mainEntityOfPage: url,
    image: [image],
    ...(input.datePublished ? { datePublished: input.datePublished } : {}),
    ...(input.dateModified || input.datePublished
      ? { dateModified: input.dateModified || input.datePublished }
      : {}),
    ...(input.section ? { articleSection: input.section } : {}),
    author: input.authorName
      ? {
          "@type": "Person",
          name: input.authorName,
          ...(input.authorUrl ? { url: toAbsoluteUrl(site, input.authorUrl) } : {}),
        }
      : {
          "@type": "Organization",
          name: siteConfig.name,
          url: toAbsoluteUrl(site, "/"),
        },
    publisher: {
      "@type": "Organization",
      name: siteConfig.name,
      logo: {
        "@type": "ImageObject",
        url: toAbsoluteUrl(site, siteConfig.logo),
      },
    },
  };
}

/** schema.org FAQPage */
export function buildFaqPageJsonLd(faqs: Faq[]) {
  return {
    "@context": "https://schema.org",
    "@type": "FAQPage",
    mainEntity: faqs.map((faq) => ({
      "@type": "Question",
      name: faq.question,
      acceptedAnswer: {
        "@type": "Answer",
        text: faqAnswerText(faq),
      },
    })),
  };
}

/** 首页：Organization + WebSite + FAQPage */
export function buildHomeJsonLd(site: URL, faqs: Faq[]) {
  return [buildOrganizationJsonLd(site), buildWebSiteJsonLd(site), buildFaqPageJsonLd(faqs)];
}

/** 平台功能页 / 定价页：FAQPage */
export function buildPlatformFaqJsonLd(items: Faq[]) {
  return buildFaqPageJsonLd(items);
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
