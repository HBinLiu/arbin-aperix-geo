import type { PageSeo } from "@/lib/seo";

export type NavLink = {
  label: string;
  href: string;
};

export type FeatureItem = {
  phase: string;
  code: string;
  title: string;
  titleBefore?: string;
  titleHighlight?: string;
  titleAfter?: string;
  tagline?: string;
  pain: string;
  solution: string;
  metrics?: string[];
  image?: string;
};

export type ComparisonRow = {
  dimension: string;
  aperix: string;
  lightweight: string;
  enterprise: string;
};

/** Payload `site-settings` 可配置项（其余首页内容见 home.ts） */
export type SiteSettings = {
  siteName: string;
  siteDescription?: string;
  navLinks?: NavLink[];
  footerLinks?: NavLink[];
  seo: PageSeo;
};

const payloadBase = import.meta.env.PUBLIC_PAYLOAD_URL || "http://127.0.0.1:4321/cms/api";

async function payloadFetch<T>(path: string): Promise<T | null> {
  try {
    const res = await fetch(`${payloadBase}${path}`, {
      headers: { Accept: "application/json" },
    });
    if (!res.ok) return null;
    return (await res.json()) as T;
  } catch {
    return null;
  }
}

export async function getSiteSettings(): Promise<SiteSettings | null> {
  return payloadFetch<SiteSettings>("/globals/site-settings?depth=0");
}
