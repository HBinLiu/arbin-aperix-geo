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
import type { CmsNewsDoc } from "@/lib/news/types";
import type { CmsBlogCategoryDoc, CmsBlogDoc } from "@/lib/blog/types";
import type { CmsAcademyCategoryDoc, CmsAcademyDoc } from "@/lib/academy/types";
import type { CmsChangelogDoc } from "@/lib/changelog/types";
import type { CmsAuthorDoc } from "@/lib/authors/types";

export type { FaqDoc, FaqPageDoc };
export type { CmsResearchCategoryDoc, CmsResearchDoc };
export type { CmsNewsDoc };
export type { CmsBlogCategoryDoc, CmsBlogDoc };
export type { CmsAcademyCategoryDoc, CmsAcademyDoc };
export type { CmsChangelogDoc };
export type { CmsAuthorDoc };

type PayloadListResponse<T> = {
  docs: T[];
  totalDocs?: number;
  totalPages?: number;
  page?: number;
  hasNextPage?: boolean;
};

const CMS_API_PATH = "/cms/api";
const ABOUT_GLOBAL_SLUG = "about-page";
const PAYLOAD_TIMEOUT_MS = import.meta.env.DEV ? 15_000 : 5_000;
/** 全量拉取时单页大小上限（禁止用单次 limit 当全站上限） */
const CMS_PAGE_SIZE_MAX = 100;

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

type FetchAllCollectionOptions = {
  collection: string;
  depth?: number;
  sort?: string;
  pageSize?: number;
  /** 默认 true：只取已发布；作者等无草稿的集合传 false */
  publishedOnly?: boolean;
};

/** 分页拉全量已发布文档（模式 A/B 共用） */
async function fetchAllCollectionDocs<T>(opts: FetchAllCollectionOptions): Promise<T[]> {
  const pageSize = Math.min(Math.max(opts.pageSize ?? CMS_PAGE_SIZE_MAX, 1), CMS_PAGE_SIZE_MAX);
  const docs: T[] = [];
  let page = 1;
  let totalPages = 1;

  do {
    const query = new URLSearchParams({
      limit: String(pageSize),
      page: String(page),
      depth: String(opts.depth ?? 1),
      sort: opts.sort ?? "-publishedAt",
    });
    if (opts.publishedOnly !== false) {
      query.set("where[_status][equals]", "published");
    }

    const data = await payloadFetch<PayloadListResponse<T>>(`/${opts.collection}?${query}`);
    if (!data?.docs?.length) break;

    docs.push(...data.docs);
    totalPages = Math.max(1, data.totalPages ?? 1);
    page += 1;
  } while (page <= totalPages);

  return docs;
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

export async function getAllResearchDocs(): Promise<CmsResearchDoc[]> {
  return fetchAllCollectionDocs<CmsResearchDoc>({
    collection: RESEARCH_COLLECTION,
    depth: 1,
    sort: "-publishedAt",
  });
}

export async function getResearchList(): Promise<CmsResearchDoc[] | null> {
  const docs = await getAllResearchDocs();
  return docs.length ? docs : null;
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

const NEWS_COLLECTION = "news";

export async function getAllNewsDocs(): Promise<CmsNewsDoc[]> {
  return fetchAllCollectionDocs<CmsNewsDoc>({
    collection: NEWS_COLLECTION,
    depth: 0,
    sort: "-publishedAt",
  });
}

export async function getNewsList(): Promise<CmsNewsDoc[] | null> {
  const docs = await getAllNewsDocs();
  return docs.length ? docs : null;
}

export async function getNewsBySlug(slug: string): Promise<CmsNewsDoc | null> {
  const query = new URLSearchParams({
    limit: "1",
    depth: "0",
    "where[slug][equals]": slug,
    "where[_status][equals]": "published",
  });
  const data = await payloadFetch<PayloadListResponse<CmsNewsDoc>>(`/${NEWS_COLLECTION}?${query}`);
  return data?.docs[0] ?? null;
}

/** 预览：读取最新草稿（需 CMS 用户 JWT） */
export async function getNewsDraftBySlug(slug: string, token: string): Promise<CmsNewsDoc | null> {
  const query = new URLSearchParams({
    limit: "1",
    depth: "0",
    draft: "true",
    "where[slug][equals]": slug,
  });
  const data = await payloadFetch<PayloadListResponse<CmsNewsDoc>>(`/${NEWS_COLLECTION}?${query}`, {
    headers: {
      Authorization: `JWT ${token.trim()}`,
    },
  });
  return data?.docs[0] ?? null;
}

const BLOG_COLLECTION = "blogs";
const BLOG_CATEGORY_COLLECTION = "blog-categories";
const AUTHORS_COLLECTION = "authors";

export async function getBlogCategories(): Promise<CmsBlogCategoryDoc[] | null> {
  const query = new URLSearchParams({
    limit: "100",
    depth: "0",
    sort: "-sortOrder",
  });
  const data = await payloadFetch<PayloadListResponse<CmsBlogCategoryDoc>>(
    `/${BLOG_CATEGORY_COLLECTION}?${query}`,
  );
  if (!data?.docs?.length) return null;
  return data.docs;
}

export async function getAllBlogDocs(): Promise<CmsBlogDoc[]> {
  return fetchAllCollectionDocs<CmsBlogDoc>({
    collection: BLOG_COLLECTION,
    // depth 2：展开 author.avatar（depth 1 时 avatar 仅为 media id）
    depth: 2,
    sort: "-publishedAt",
  });
}

export async function getBlogList(): Promise<CmsBlogDoc[] | null> {
  const docs = await getAllBlogDocs();
  return docs.length ? docs : null;
}

export async function getBlogBySlug(slug: string): Promise<CmsBlogDoc | null> {
  const query = new URLSearchParams({
    limit: "1",
    depth: "2",
    "where[slug][equals]": slug,
    "where[_status][equals]": "published",
  });
  const data = await payloadFetch<PayloadListResponse<CmsBlogDoc>>(`/${BLOG_COLLECTION}?${query}`);
  return data?.docs[0] ?? null;
}

export async function getBlogDraftBySlug(slug: string, token: string): Promise<CmsBlogDoc | null> {
  const query = new URLSearchParams({
    limit: "1",
    depth: "2",
    draft: "true",
    "where[slug][equals]": slug,
  });
  const data = await payloadFetch<PayloadListResponse<CmsBlogDoc>>(`/${BLOG_COLLECTION}?${query}`, {
    headers: {
      Authorization: `JWT ${token.trim()}`,
    },
  });
  return data?.docs[0] ?? null;
}

const ACADEMY_COLLECTION = "academies";
const ACADEMY_CATEGORY_COLLECTION = "academy-categories";

export async function getAcademyCategories(): Promise<CmsAcademyCategoryDoc[] | null> {
  const query = new URLSearchParams({
    limit: "100",
    depth: "0",
    sort: "-sortOrder",
  });
  const data = await payloadFetch<PayloadListResponse<CmsAcademyCategoryDoc>>(
    `/${ACADEMY_CATEGORY_COLLECTION}?${query}`,
  );
  if (!data?.docs?.length) return null;
  return data.docs;
}

export async function getAllAcademyDocs(): Promise<CmsAcademyDoc[]> {
  return fetchAllCollectionDocs<CmsAcademyDoc>({
    collection: ACADEMY_COLLECTION,
    depth: 1,
    sort: "-publishedAt",
  });
}

export async function getAcademyList(): Promise<CmsAcademyDoc[] | null> {
  const docs = await getAllAcademyDocs();
  return docs.length ? docs : null;
}

export async function getAcademyBySlug(slug: string): Promise<CmsAcademyDoc | null> {
  const query = new URLSearchParams({
    limit: "1",
    depth: "1",
    "where[slug][equals]": slug,
    "where[_status][equals]": "published",
  });
  const data = await payloadFetch<PayloadListResponse<CmsAcademyDoc>>(
    `/${ACADEMY_COLLECTION}?${query}`,
  );
  return data?.docs[0] ?? null;
}

export async function getAcademyDraftBySlug(
  slug: string,
  token: string,
): Promise<CmsAcademyDoc | null> {
  const query = new URLSearchParams({
    limit: "1",
    depth: "1",
    draft: "true",
    "where[slug][equals]": slug,
  });
  const data = await payloadFetch<PayloadListResponse<CmsAcademyDoc>>(
    `/${ACADEMY_COLLECTION}?${query}`,
    {
      headers: {
        Authorization: `JWT ${token.trim()}`,
      },
    },
  );
  return data?.docs[0] ?? null;
}

const CHANGELOG_COLLECTION = "changelogs";

export async function getAllChangelogDocs(): Promise<CmsChangelogDoc[]> {
  return fetchAllCollectionDocs<CmsChangelogDoc>({
    collection: CHANGELOG_COLLECTION,
    depth: 2,
    sort: "-publishedAt",
  });
}

export async function getChangelogList(): Promise<CmsChangelogDoc[] | null> {
  const docs = await getAllChangelogDocs();
  return docs.length ? docs : null;
}

export async function getChangelogBySlug(slug: string): Promise<CmsChangelogDoc | null> {
  const query = new URLSearchParams({
    limit: "1",
    depth: "2",
    "where[slug][equals]": slug,
    "where[_status][equals]": "published",
  });
  const data = await payloadFetch<PayloadListResponse<CmsChangelogDoc>>(
    `/${CHANGELOG_COLLECTION}?${query}`,
  );
  return data?.docs[0] ?? null;
}

export async function getChangelogDraftBySlug(
  slug: string,
  token: string,
): Promise<CmsChangelogDoc | null> {
  const query = new URLSearchParams({
    limit: "1",
    depth: "2",
    draft: "true",
    "where[slug][equals]": slug,
  });
  const data = await payloadFetch<PayloadListResponse<CmsChangelogDoc>>(
    `/${CHANGELOG_COLLECTION}?${query}`,
    {
      headers: {
        Authorization: `JWT ${token.trim()}`,
      },
    },
  );
  return data?.docs[0] ?? null;
}

export async function getAllAuthorDocs(): Promise<CmsAuthorDoc[]> {
  return fetchAllCollectionDocs<CmsAuthorDoc>({
    collection: AUTHORS_COLLECTION,
    depth: 1,
    sort: "-sortOrder",
    publishedOnly: false,
  });
}

export async function getAuthors(): Promise<CmsAuthorDoc[] | null> {
  const docs = await getAllAuthorDocs();
  return docs.length ? docs : null;
}

export async function getAuthorBySlug(slug: string): Promise<CmsAuthorDoc | null> {
  const query = new URLSearchParams({
    limit: "1",
    depth: "1",
    "where[slug][equals]": slug,
  });
  const data = await payloadFetch<PayloadListResponse<CmsAuthorDoc>>(
    `/${AUTHORS_COLLECTION}?${query}`,
  );
  return data?.docs[0] ?? null;
}
