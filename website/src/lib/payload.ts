import type { CmsSeoMeta, PageSeo } from "@/lib/seo";

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

/** Payload SEO 插件 meta 字段 */

export type CmsPageStory = {
  title?: string;
  content?: Record<string, unknown> | null;
};

export type CmsAboutPage = {
  story?: CmsPageStory;
};

export type CmsPageSeoEntry = {
  path: string;
  label?: string;
  noindex?: boolean;
  meta?: CmsSeoMeta;
};

import type { FaqDoc, FaqPageDoc } from "@shared/faq";
import type { CmsResearchCategoryDoc, CmsResearchDoc } from "@/lib/research/types";

export type { FaqDoc, FaqPageDoc };
export type { CmsResearchCategoryDoc, CmsResearchDoc };

type PayloadListResponse<T> = {
  docs: T[];
};

const CMS_API_PATH = "/cms/api";
const ABOUT_GLOBAL_SLUG = "about-page";
const PAYLOAD_TIMEOUT_MS = import.meta.env.DEV ? 15_000 : 5_000;

export function payloadApiBase(): string {
  const configured = (import.meta.env.PAYLOAD_API_URL || CMS_API_PATH).replace(/\/$/, "");

  if (configured.startsWith("http://") || configured.startsWith("https://")) {
    return configured.endsWith(CMS_API_PATH) ? configured : `${configured}${CMS_API_PATH}`;
  }

  const path = configured.startsWith("/") ? configured : `/${configured}`;

  if (import.meta.env.DEV) {
    return `http://localhost:3000${path}`;
  }

  const site = import.meta.env.SITE?.replace(/\/$/, "");
  return site ? `${site}${path}` : path;
}

async function payloadFetch<T>(path: string, init?: RequestInit): Promise<T | null> {
  try {
    const res = await fetch(`${payloadApiBase()}${path}`, {
      headers: { Accept: "application/json", ...init?.headers },
      signal: AbortSignal.timeout(PAYLOAD_TIMEOUT_MS),
      ...init,
    });
    if (!res.ok) return null;
    return (await res.json()) as T;
  } catch {
    return null;
  }
}

export async function getAboutPage(): Promise<CmsAboutPage | null> {
  const query = new URLSearchParams({ depth: "0" });
  return payloadFetch<CmsAboutPage>(`/globals/${ABOUT_GLOBAL_SLUG}?${query}`);
}

function normalizeSitePath(path: string): string {
  if (!path || path === "/") return "/";
  return path.endsWith("/") ? path : `${path}/`;
}

let pageSeoCache: Map<string, CmsPageSeoEntry> | null = null;

async function loadPageSeoMap(): Promise<Map<string, CmsPageSeoEntry>> {
  if (pageSeoCache) return pageSeoCache;

  const query = new URLSearchParams({ limit: "200", depth: "1" });
  const data = await payloadFetch<PayloadListResponse<CmsPageSeoEntry>>(`/page-seo?${query}`);
  pageSeoCache = new Map(
    (data?.docs ?? []).map((doc) => [normalizeSitePath(doc.path), doc]),
  );
  return pageSeoCache;
}

export async function getPageSeoByPath(path: string): Promise<CmsPageSeoEntry | null> {
  const map = await loadPageSeoMap();
  return map.get(normalizeSitePath(path)) ?? null;
}

export async function getFaqsByPage(page: string): Promise<FaqDoc[] | null> {
  const query = new URLSearchParams({
    "where[page][equals]": page,
    limit: "1",
    depth: "0",
  });
  const data = await payloadFetch<PayloadListResponse<FaqPageDoc>>(`/faqs?${query}`);
  const doc = data?.docs[0];
  if (!doc?.items?.length) return null;
  return doc.items;
}

/** @deprecated 使用 getFaqsByPage(FAQ_PAGE.home) */
export async function getHomeFaqs(): Promise<FaqDoc[] | null> {
  return getFaqsByPage("home");
}

const RESEARCH_COLLECTION = "researches";
const RESEARCH_CATEGORY_COLLECTION = "research-categories";

export async function getResearchCategories(): Promise<CmsResearchCategoryDoc[] | null> {
  const query = new URLSearchParams({
    limit: "100",
    depth: "0",
    sort: "-sortOrder",
  });
  const data = await payloadFetch<PayloadListResponse<CmsResearchCategoryDoc>>(
    `/${RESEARCH_CATEGORY_COLLECTION}?${query}`,
  );
  if (!data?.docs?.length) return null;
  return data.docs;
}

export async function getResearchList(): Promise<CmsResearchDoc[] | null> {
  const query = new URLSearchParams({
    limit: "100",
    depth: "1",
    sort: "-publishedAt",
    "where[_status][equals]": "published",
  });
  const data = await payloadFetch<PayloadListResponse<CmsResearchDoc>>(
    `/${RESEARCH_COLLECTION}?${query}`,
  );
  if (!data?.docs?.length) return null;
  return data.docs;
}

export async function getResearchBySlug(slug: string): Promise<CmsResearchDoc | null> {
  const query = new URLSearchParams({
    limit: "1",
    depth: "1",
    "where[slug][equals]": slug,
    "where[_status][equals]": "published",
  });
  const data = await payloadFetch<PayloadListResponse<CmsResearchDoc>>(
    `/${RESEARCH_COLLECTION}?${query}`,
  );
  return data?.docs[0] ?? null;
}

/** 预览：读取最新草稿（需 CMS 用户 JWT） */
export async function getResearchDraftBySlug(
  slug: string,
  token: string,
): Promise<CmsResearchDoc | null> {
  const query = new URLSearchParams({
    limit: "1",
    depth: "1",
    draft: "true",
    "where[slug][equals]": slug,
  });
  const data = await payloadFetch<PayloadListResponse<CmsResearchDoc>>(
    `/${RESEARCH_COLLECTION}?${query}`,
    {
      headers: {
        Authorization: `JWT ${token.trim()}`,
      },
    },
  );
  return data?.docs[0] ?? null;
}
