import type { PlatformId } from "@shared/platform";
import {
  CORE_PAGE_SEO,
  MONITOR_PAGE_SEO,
  PLATFORM_PAGE_SEO,
  type PageSeoDefault,
} from "@shared/seo/defaults";
import { siteConfig } from "@site";
import { resolveSiteCopy, sitePageTitle } from "@/lib/site";

export type PageSeo = {
  title: string;
  description: string;
  canonicalPath?: string;
  image?: string;
  type?: "website" | "article";
  noindex?: boolean;
};

export type CmsMedia = {
  url?: string | null;
};

/** Payload SEO 插件 meta 字段 */
export type CmsSeoMeta = {
  title?: string | null;
  description?: string | null;
  image?: CmsMedia | string | null;
};

export type ResolvedPageMeta = {
  title: string;
  description: string;
  canonical: string;
  image: string;
  type: "website" | "article";
  siteName: string;
  noindex: boolean;
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

export function toPageSeo(defaults: PageSeoDefault): PageSeo {
  return {
    title: sitePageTitle(defaults.titleTopic),
    description: resolveSiteCopy(defaults.description),
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

/** 将 Payload SEO 插件 `meta` 转为 PageSeo 局部覆盖（未设 OG 图时回退 site.config 默认图） */
export function cmsMetaToPageSeo(meta?: CmsSeoMeta | null): Partial<PageSeo> | null {
  if (!meta) return null;

  const title = meta.title?.trim();
  const description = meta.description?.trim();
  const image = resolveCmsMediaUrl(meta.image);

  if (!title && !description && !image) return null;

  return {
    ...(title ? { title: resolveSiteCopy(title) } : {}),
    ...(description ? { description: resolveSiteCopy(description) } : {}),
    ...(image ? { image } : {}),
  };
}

/** 将 PageSeo 解析为 head 所需的 canonical / OG / Twitter 字段；site 来自 Astro.site（astro.config site） */
export function resolvePageMeta(seo: PageSeo, site: URL, pathname: string): ResolvedPageMeta {
  const canonical = toAbsoluteUrl(normalizePathname(seo.canonicalPath ?? pathname), site);

  return {
    title: seo.title,
    description: seo.description,
    canonical,
    image: toAbsoluteUrl(seo.image ?? siteConfig.ogImage, site),
    type: seo.type ?? "website",
    siteName: siteConfig.name,
    noindex: seo.noindex ?? false,
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
