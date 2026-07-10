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

function payloadApiBase(): string {
  const configured = (import.meta.env.PAYLOAD_API_URL || "/cms/api").replace(/\/$/, "");
  if (configured.startsWith("http://") || configured.startsWith("https://")) {
    return configured;
  }

  const path = configured.startsWith("/") ? configured : `/${configured}`;

  if (import.meta.env.DEV) {
    return `http://127.0.0.1:3000${path}`;
  }

  const site = import.meta.env.SITE?.replace(/\/$/, "");
  return site ? `${site}${path}` : path;
}

async function payloadFetch<T>(path: string): Promise<T | null> {
  try {
    const res = await fetch(`${payloadApiBase()}${path}`, {
      headers: { Accept: "application/json" },
      signal: AbortSignal.timeout(5_000),
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
