import type { PlatformId } from "@shared/platform";
import { CORE_PAGE_SEO } from "@shared/seo/defaults/core";
import { MONITOR_PAGE_SEO } from "@shared/seo/defaults/monitor";
import { PLATFORM_PAGE_SEO } from "@shared/seo/defaults/platform";
import type { PageSeoDefault } from "@shared/seo/defaults/types";
import { siteConfig } from "@site";
import { resolveSiteCopy, sitePageTitle } from "@/lib/site";

/** 默认 OG 图尺寸（与 shared/assets/images/website/og-default.webp 一致） */
export const DEFAULT_OG_IMAGE = {
  width: 1200,
  height: 630,
  type: "image/webp",
} as const;

export type PageSeo = {
  title: string;
  description: string;
  keywords?: string;
  canonicalPath?: string;
  image?: string;
  /** OG / Twitter 分享图替代文本；缺省回退为页面 title */
  imageAlt?: string;
  imageWidth?: number;
  imageHeight?: number;
  imageType?: string;
  type?: "website" | "article";
  noindex?: boolean;
  /** article:published_time（ISO） */
  publishedTime?: string;
  /** article:modified_time（ISO） */
  modifiedTime?: string;
  /** article:author */
  authorName?: string;
  /** article:section */
  section?: string;
};

export type CmsMedia = {
  url?: string | null;
  alt?: string | null;
  width?: number | null;
  height?: number | null;
  mimeType?: string | null;
};

/** Payload SEO 插件 meta 字段 */
export type CmsSeoMeta = {
  title?: string | null;
  description?: string | null;
  keywords?: string | null;
  image?: CmsMedia | string | null;
};

export type ResolvedPageMeta = {
  title: string;
  description: string;
  keywords: string;
  canonical: string;
  image: string;
  imageAlt: string;
  imageWidth: number;
  imageHeight: number;
  imageType: string;
  type: "website" | "article";
  siteName: string;
  noindex: boolean;
  robots: string;
  publishedTime?: string;
  modifiedTime?: string;
  authorName?: string;
  section?: string;
};

function normalizePathname(pathname: string): string {
  if (pathname === "/" || pathname.endsWith("/")) return pathname;
  return `${pathname}/`;
}

function toAbsoluteUrl(pathOrUrl: string, base: URL): string {
  if (pathOrUrl.startsWith("http://") || pathOrUrl.startsWith("https://")) {
    return pathOrUrl;
  }
  return new URL(pathOrUrl, base).href;
}

/** 解析为 ISO 8601；无效则返回 undefined */
export function toIsoDate(value: string | null | undefined): string | undefined {
  if (!value?.trim()) return undefined;
  const ms = Date.parse(value);
  if (Number.isNaN(ms)) return undefined;
  return new Date(ms).toISOString();
}

/** 给详情 SEO 附上 article 元数据 */
export function withArticleMeta(
  seo: PageSeo,
  fields: {
    publishedTime?: string | null;
    modifiedTime?: string | null;
    authorName?: string | null;
    section?: string | null;
  },
): PageSeo {
  const publishedTime = toIsoDate(fields.publishedTime);
  const modifiedTime = toIsoDate(fields.modifiedTime) || publishedTime;
  const authorName = fields.authorName?.trim() || undefined;
  const section = fields.section?.trim() || undefined;

  return {
    ...seo,
    ...(publishedTime ? { publishedTime } : {}),
    ...(modifiedTime ? { modifiedTime } : {}),
    ...(authorName ? { authorName } : {}),
    ...(section ? { section } : {}),
  };
}

export function toPageSeo(defaults: PageSeoDefault): PageSeo {
  return {
    title: sitePageTitle(defaults.titleTopic),
    description: resolveSiteCopy(defaults.description),
    ...(defaults.keywords ? { keywords: resolveSiteCopy(defaults.keywords) } : {}),
  };
}

/** CMS / 运行时覆盖：空字段回退到 defaults */
export function mergePageSeo(base: PageSeo, override?: Partial<PageSeo> | null): PageSeo {
  if (!override) return base;
  return {
    ...base,
    ...override,
    title: resolveSiteCopy(override.title?.trim() || base.title),
    description: resolveSiteCopy(override.description?.trim() || base.description),
    keywords: override.keywords?.trim() || base.keywords,
    imageAlt: override.imageAlt?.trim() || base.imageAlt,
    publishedTime: override.publishedTime || base.publishedTime,
    modifiedTime: override.modifiedTime || base.modifiedTime,
    authorName: override.authorName?.trim() || base.authorName,
    section: override.section?.trim() || base.section,
    imageWidth: override.imageWidth ?? base.imageWidth,
    imageHeight: override.imageHeight ?? base.imageHeight,
    imageType: override.imageType?.trim() || base.imageType,
  };
}

function cmsAssetUrl(path: string): string {
  const normalized = path.startsWith("/") ? path : `/${path}`;
  if (import.meta.env.DEV) {
    return `http://127.0.0.1:3000${normalized}`;
  }
  const site = import.meta.env.SITE?.replace(/\/$/, "");
  return site ? `${site}${normalized}` : normalized;
}

/** 解析 Payload Media 或路径为绝对/可用 URL */
export function resolveCmsMediaUrl(image: CmsSeoMeta["image"]): string | undefined {
  if (!image) return undefined;
  if (typeof image === "string") {
    return image.startsWith("http") ? image : cmsAssetUrl(image);
  }
  const url = image.url?.trim();
  if (!url) return undefined;
  return url.startsWith("http") ? url : cmsAssetUrl(url);
}

function resolveCmsMediaAlt(image: CmsSeoMeta["image"]): string | undefined {
  if (!image || typeof image === "string") return undefined;
  const alt = image.alt?.trim();
  return alt || undefined;
}

function resolveCmsMediaDimensions(image: CmsSeoMeta["image"]): {
  imageWidth?: number;
  imageHeight?: number;
  imageType?: string;
} {
  if (!image || typeof image === "string") return {};
  return {
    ...(typeof image.width === "number" && image.width > 0 ? { imageWidth: image.width } : {}),
    ...(typeof image.height === "number" && image.height > 0 ? { imageHeight: image.height } : {}),
    ...(image.mimeType?.trim() ? { imageType: image.mimeType.trim() } : {}),
  };
}

/** 将 Payload SEO 插件 `meta` 转为 PageSeo 局部覆盖（未设 OG 图时回退 site.config 默认图） */
export function cmsMetaToPageSeo(meta?: CmsSeoMeta | null): Partial<PageSeo> | null {
  if (!meta) return null;

  const title = meta.title?.trim();
  const description = meta.description?.trim();
  const keywords = meta.keywords?.trim();
  const image = resolveCmsMediaUrl(meta.image);
  const imageAlt = resolveCmsMediaAlt(meta.image);
  const dims = resolveCmsMediaDimensions(meta.image);

  if (!title && !description && !keywords && !image && !imageAlt) return null;

  return {
    ...(title ? { title: resolveSiteCopy(title) } : {}),
    ...(description ? { description: resolveSiteCopy(description) } : {}),
    ...(keywords ? { keywords: resolveSiteCopy(keywords) } : {}),
    ...(image ? { image } : {}),
    ...(imageAlt ? { imageAlt } : {}),
    ...dims,
  };
}

/** 将 PageSeo 解析为 head 所需的 canonical / OG / Twitter 字段；site 来自 Astro.site（astro.config site） */
export function resolvePageMeta(seo: PageSeo, site: URL, pathname: string): ResolvedPageMeta {
  const canonical = toAbsoluteUrl(normalizePathname(seo.canonicalPath ?? pathname), site);
  const usingDefaultImage = !seo.image?.trim();

  return {
    title: seo.title,
    description: seo.description,
    keywords: seo.keywords?.trim() || siteConfig.keywords,
    canonical,
    image: toAbsoluteUrl(seo.image ?? siteConfig.ogImage, site),
    imageAlt: seo.imageAlt?.trim() || seo.title,
    imageWidth: seo.imageWidth ?? DEFAULT_OG_IMAGE.width,
    imageHeight: seo.imageHeight ?? DEFAULT_OG_IMAGE.height,
    imageType: seo.imageType?.trim() || (usingDefaultImage ? DEFAULT_OG_IMAGE.type : "image/jpeg"),
    type: seo.type ?? "website",
    siteName: siteConfig.name,
    noindex: seo.noindex ?? false,
    robots: seo.noindex ? "noindex, follow" : "index, follow",
    publishedTime: seo.publishedTime,
    modifiedTime: seo.modifiedTime,
    authorName: seo.authorName,
    section: seo.section,
  };
}

/** 首页 */
export const homeSeo = toPageSeo(CORE_PAGE_SEO.home);

/** 关于我们 */
export const aboutSeo = toPageSeo(CORE_PAGE_SEO.about);

/** 联系我们 / 预约演示 */
export const contactSeo = toPageSeo(CORE_PAGE_SEO.contact);

/** 定价 */
export const pricingSeo = toPageSeo(CORE_PAGE_SEO.pricing);

/** 研究 */
export const researchSeo = toPageSeo(CORE_PAGE_SEO.research);

/** 新闻 */
export const newsSeo = toPageSeo(CORE_PAGE_SEO.news);

/** 博客 */
export const blogSeo = toPageSeo(CORE_PAGE_SEO.blog);

/** 学院 */
export const academySeo = toPageSeo(CORE_PAGE_SEO.academy);

/** 更新日志 */
export const changelogsSeo = toPageSeo(CORE_PAGE_SEO.changelogs);

/** 免费工具 · 单页审计 */
export const singlePageAuditSeo = toPageSeo(CORE_PAGE_SEO.singlePageAudit);

/** 免费工具 · LLMs.txt 生成器 */
export const llmsTxtGeneratorSeo = toPageSeo(CORE_PAGE_SEO.llmsTxtGenerator);

/** 免费工具 · 热门提示词发现器 */
export const hotPromptFinderSeo = toPageSeo(CORE_PAGE_SEO.hotPromptFinder);

/** 服务 · GEO 官网定制 */
export const geoWebsiteSeo = toPageSeo(CORE_PAGE_SEO.geoWebsite);

/** 研究报告详情 */
export function researchDetailSeo(report: { title: string; description: string; slug: string }) {
  return {
    ...toPageSeo({
      label: report.title,
      path: `/research/${report.slug}/`,
      titleTopic: report.title,
      description: report.description,
    }),
    canonicalPath: `/research/${report.slug}/`,
    type: "article" as const,
  };
}

/** CMS meta 覆盖卡片默认；OG 图未设时可回退封面 */
export function mergeResearchDetailSeo(
  report: { title: string; description: string; slug: string },
  meta?: CmsSeoMeta | null,
  fallbackImage?: string,
): PageSeo {
  const merged = mergePageSeo(researchDetailSeo(report), cmsMetaToPageSeo(meta));
  if (!merged.image && fallbackImage) {
    return { ...merged, image: fallbackImage };
  }
  return merged;
}

/** 新闻详情 */
export function newsDetailSeo(article: { title: string; description: string; slug: string }) {
  return {
    ...toPageSeo({
      label: article.title,
      path: `/news/${article.slug}/`,
      titleTopic: article.title,
      description: article.description,
    }),
    canonicalPath: `/news/${article.slug}/`,
    type: "article" as const,
  };
}

/** CMS meta 覆盖卡片默认 */
export function mergeNewsDetailSeo(
  article: { title: string; description: string; slug: string },
  meta?: CmsSeoMeta | null,
): PageSeo {
  return mergePageSeo(newsDetailSeo(article), cmsMetaToPageSeo(meta));
}

/** 博客详情 */
export function blogDetailSeo(article: { title: string; description: string; slug: string }) {
  return {
    ...toPageSeo({
      label: article.title,
      path: `/blog/${article.slug}/`,
      titleTopic: article.title,
      description: article.description,
    }),
    canonicalPath: `/blog/${article.slug}/`,
    type: "article" as const,
  };
}

export function mergeBlogDetailSeo(
  article: { title: string; description: string; slug: string },
  meta?: CmsSeoMeta | null,
  fallbackImage?: string,
): PageSeo {
  const merged = mergePageSeo(blogDetailSeo(article), cmsMetaToPageSeo(meta));
  if (!merged.image && fallbackImage) {
    return { ...merged, image: fallbackImage };
  }
  return merged;
}

/** 学院详情 */
export function academyDetailSeo(article: { title: string; description: string; slug: string }) {
  return {
    ...toPageSeo({
      label: article.title,
      path: `/academy/${article.slug}/`,
      titleTopic: article.title,
      description: article.description,
    }),
    canonicalPath: `/academy/${article.slug}/`,
    type: "article" as const,
  };
}

export function mergeAcademyDetailSeo(
  article: { title: string; description: string; slug: string },
  meta?: CmsSeoMeta | null,
  fallbackImage?: string,
): PageSeo {
  const merged = mergePageSeo(academyDetailSeo(article), cmsMetaToPageSeo(meta));
  if (!merged.image && fallbackImage) {
    return { ...merged, image: fallbackImage };
  }
  return merged;
}

/** 更新日志详情 */
export function changelogDetailSeo(article: { title: string; description: string; slug: string }) {
  return {
    ...toPageSeo({
      label: article.title,
      path: `/changelogs/${article.slug}/`,
      titleTopic: article.title,
      description: article.description,
    }),
    canonicalPath: `/changelogs/${article.slug}/`,
    type: "article" as const,
  };
}

export function mergeChangelogDetailSeo(
  article: { title: string; description: string; slug: string },
  meta?: CmsSeoMeta | null,
): PageSeo {
  return mergePageSeo(changelogDetailSeo(article), cmsMetaToPageSeo(meta));
}

/** 作者详情 */
export function authorDetailSeo(author: { name: string; bio: string; slug: string }) {
  return {
    ...toPageSeo({
      label: author.name,
      path: `/authors/${author.slug}/`,
      titleTopic: author.name,
      description: author.bio,
    }),
    canonicalPath: `/authors/${author.slug}/`,
  };
}

export function mergeAuthorDetailSeo(
  author: { name: string; bio: string; slug: string },
  meta?: CmsSeoMeta | null,
): PageSeo {
  return mergePageSeo(authorDetailSeo(author), cmsMetaToPageSeo(meta));
}

/** 平台能力页 */
export const platformAnswerSeo = toPageSeo(PLATFORM_PAGE_SEO.answer);
export const platformTopicSeo = toPageSeo(PLATFORM_PAGE_SEO.topics);
export const platformPromptSeo = toPageSeo(PLATFORM_PAGE_SEO.prompt);
export const platformContentSeo = toPageSeo(PLATFORM_PAGE_SEO.content);

/** 各 AI 平台监测落地页 */
export const platformMonitorSeo: Record<PlatformId, PageSeo> = Object.fromEntries(
  Object.entries(MONITOR_PAGE_SEO).map(([platformId, defaults]) => [
    platformId,
    toPageSeo(defaults),
  ]),
) as Record<PlatformId, PageSeo>;
