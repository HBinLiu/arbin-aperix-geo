import { siteConfig } from "@site";

const SITE_NAME_PLACEHOLDER = /\{\{siteName\}\}/g;

/** 将文案中的 `{{siteName}}` 替换为 site.config.mjs 中的品牌名 */
export function resolveSiteCopy(value: string): string {
  return value.replace(SITE_NAME_PLACEHOLDER, siteConfig.name);
}

/** 递归替换对象 / 数组中所有字符串里的 `{{siteName}}` */
export function resolveSiteCopyDeep<T>(value: T): T {
  if (typeof value === "string") return resolveSiteCopy(value) as T;
  if (Array.isArray(value)) return value.map((item) => resolveSiteCopyDeep(item)) as T;
  if (value !== null && typeof value === "object") {
    return Object.fromEntries(
      Object.entries(value as Record<string, unknown>).map(([key, entry]) => [
        key,
        resolveSiteCopyDeep(entry),
      ]),
    ) as T;
  }
  return value;
}

/** 全站 `<title>` 格式：`{页面主题} | {品牌名}` */
export function sitePageTitle(topic: string): string {
  return `${topic} | ${siteConfig.name}`;
}
