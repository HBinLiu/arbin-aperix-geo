import type { CollectionAfterChangeHook, CollectionSlug } from "payload";

import { pushUrlsToBaidu, isBaiduPushEnabled } from "./baiduPush";
import { getWebsiteUrl } from "./urls";

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

function publicUrlFor(collection: CollectionSlug, slug: string): string | null {
  const builder = PUBLIC_PATH_BY_COLLECTION[collection];
  if (!builder) return null;
  const base = getWebsiteUrl().replace(/\/$/, "");
  // 本地开发默认不推真实百度；仅当网站 URL 为 https 公网时推送
  if (!/^https:\/\//i.test(base)) return null;
  return `${base}${builder(slug)}`;
}

function docSlug(doc: Record<string, unknown>): string {
  return typeof doc.slug === "string" ? doc.slug.trim() : "";
}

function isPublished(doc: Record<string, unknown>): boolean {
  // 无草稿集合（如 authors）视为始终可推
  if (!("_status" in doc)) return true;
  return doc._status === "published";
}

/**
 * 发布成功后异步推送到百度普通收录。
 * 未配置 BAIDU_PUSH_* 或官网非 https 时跳过。
 */
export function createBaiduPushAfterChangeHook(
  collection: CollectionSlug,
): CollectionAfterChangeHook {
  return async ({ doc, previousDoc, operation }) => {
    if (!isBaiduPushEnabled()) return doc;

    const current = doc as Record<string, unknown>;
    if (!isPublished(current)) return doc;

    const slug = docSlug(current);
    if (!slug) return doc;

    const prev = previousDoc as Record<string, unknown> | undefined;
    const wasPublished = prev ? isPublished(prev) : false;
    const prevSlug = prev ? docSlug(prev) : "";

    // 首次发布，或已发布状态下改了 slug：推送新 URL
    const shouldPush =
      operation === "create" || !wasPublished || (wasPublished && prevSlug && prevSlug !== slug);
    if (!shouldPush) return doc;

    const url = publicUrlFor(collection, slug);
    if (!url) return doc;

    // 不阻塞保存；后台推送
    void pushUrlsToBaidu([url]).then((result) => {
      if (result.ok) {
        console.info(
          `[baidu-push] ${collection}/${slug} ok success=${result.success ?? "?"} remain=${result.remain ?? "?"}`,
        );
      } else {
        console.warn(
          `[baidu-push] ${collection}/${slug} fail: ${result.message || result.raw || result.status}`,
        );
      }
    });

    return doc;
  };
}
