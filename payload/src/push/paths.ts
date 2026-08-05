import type { CollectionSlug } from "payload";

import { getWebsiteUrl } from "../lib/urls";

/** 内容集合 → 官网公开路径（正式页，非 preview） */
const PUBLIC_PATH_BY_COLLECTION: Partial<
  Record<CollectionSlug, (slug: string) => string>
> = {
  researches: (slug) => `/research/${encodeURIComponent(slug)}/`,
  news: (slug) => `/news/${encodeURIComponent(slug)}/`,
  blogs: (slug) => `/blog/${encodeURIComponent(slug)}/`,
  academies: (slug) => `/academy/${encodeURIComponent(slug)}/`,
  changelogs: (slug) => `/changelogs/${encodeURIComponent(slug)}/`,
  authors: (slug) => `/authors/${encodeURIComponent(slug)}/`,
};

export function publicUrlFor(collection: CollectionSlug, slug: string): string | null {
  const builder = PUBLIC_PATH_BY_COLLECTION[collection];
  if (!builder) return null;
  const base = getWebsiteUrl().replace(/\/$/, "");
  // 本地开发默认不推；仅当网站 URL 为 https 公网时推送
  if (!/^https:\/\//i.test(base)) return null;
  return `${base}${builder(slug)}`;
}

export function docSlug(doc: Record<string, unknown>): string {
  return typeof doc.slug === "string" ? doc.slug.trim() : "";
}

export function isPublished(doc: Record<string, unknown>): boolean {
  // 无草稿集合（如 authors）视为始终可推
  if (!("_status" in doc)) return true;
  return doc._status === "published";
}

/** 首次发布，或已发布状态下改了 slug */
export function shouldPushOnChange(options: {
  operation: string;
  wasPublished: boolean;
  prevSlug: string;
  slug: string;
}): boolean {
  const { operation, wasPublished, prevSlug, slug } = options;
  return (
    operation === "create" ||
    !wasPublished ||
    (wasPublished && Boolean(prevSlug) && prevSlug !== slug)
  );
}
