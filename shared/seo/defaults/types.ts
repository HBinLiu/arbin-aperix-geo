import type { PlatformId } from "../../platform.ts";

/** 单页默认 SEO（title 为主题，不含 `| 品牌名`；description 可含 {{siteName}}） */
export type PageSeoDefault = {
  label: string;
  path: string;
  titleTopic: string;
  description: string;
  noindex?: boolean;
};

export type MonitorPageSeoDefault = PageSeoDefault & {
  platformId: PlatformId;
};

export const SITE_NAME_PLACEHOLDER = "{{siteName}}";

/** Payload `page-seo` collection 的 meta.title 格式 */
export function cmsPageSeoTitle(titleTopic: string): string {
  return `${titleTopic} | ${SITE_NAME_PLACEHOLDER}`;
}

export type CmsPageSeoSeedEntry = {
  label: string;
  path: string;
  meta: {
    title: string;
    description: string;
  };
  noindex?: boolean;
};

export function toCmsPageSeoSeed(defaults: PageSeoDefault): CmsPageSeoSeedEntry {
  return {
    label: defaults.label,
    path: defaults.path,
    meta: {
      title: cmsPageSeoTitle(defaults.titleTopic),
      description: defaults.description,
    },
    noindex: defaults.noindex,
  };
}
