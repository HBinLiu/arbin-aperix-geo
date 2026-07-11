import type { PageSeo } from "@/lib/seo";

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

/** Payload `about-page` Global 类型 */

export type CmsPageStoryParagraph = {
  text: string;
};

export type CmsPageStory = {
  title?: string;
  paragraphs?: CmsPageStoryParagraph[];
};

export type CmsAboutPage = {
  story?: CmsPageStory;
  seo?: PageSeo;
};

export type CmsFaq = {
  question: string;
  answer: string;
  sortOrder: number;
  page?: string;
};

type PayloadListResponse<T> = {
  docs: T[];
};

const CMS_API_PATH = "/cms/api";
const ABOUT_GLOBAL_SLUG = "about-page";
const PAYLOAD_TIMEOUT_MS = import.meta.env.DEV ? 2_000 : 5_000;

function payloadApiBase(): string {
  const configured = (import.meta.env.PAYLOAD_API_URL || CMS_API_PATH).replace(/\/$/, "");

  if (configured.startsWith("http://") || configured.startsWith("https://")) {
    return configured.endsWith(CMS_API_PATH) ? configured : `${configured}${CMS_API_PATH}`;
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
      signal: AbortSignal.timeout(PAYLOAD_TIMEOUT_MS),
    });
    if (!res.ok) return null;
    return (await res.json()) as T;
  } catch {
    return null;
  }
}

export async function getAboutPage(): Promise<CmsAboutPage | null> {
  return payloadFetch<CmsAboutPage>(`/globals/${ABOUT_GLOBAL_SLUG}`);
}

export async function getHomeFaqs(): Promise<CmsFaq[] | null> {
  const query = new URLSearchParams({
    "where[page][equals]": "home",
    sort: "sortOrder",
    limit: "100",
    depth: "0",
  });
  const data = await payloadFetch<PayloadListResponse<CmsFaq>>(`/faqs?${query}`);
  if (!data?.docs.length) return null;
  return data.docs;
}
