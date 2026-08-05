import type { CollectionAfterChangeHook, CollectionSlug } from "payload";

import { pushUrlsToIndexNow, isIndexNowPushEnabled } from "./client";
import {
  docSlug,
  isPublished,
  publicUrlFor,
  shouldPushOnChange,
} from "../paths";

/**
 * 发布成功后异步推送到 IndexNow（Bing 等）。
 * 未配置 INDEXNOW_KEY 或官网非 https 时跳过。
 */
export function createIndexNowPushAfterChangeHook(
  collection: CollectionSlug,
): CollectionAfterChangeHook {
  return async ({ doc, previousDoc, operation }) => {
    if (!isIndexNowPushEnabled()) return doc;

    const current = doc as Record<string, unknown>;
    if (!isPublished(current)) return doc;

    const slug = docSlug(current);
    if (!slug) return doc;

    const prev = previousDoc as Record<string, unknown> | undefined;
    const wasPublished = prev ? isPublished(prev) : false;
    const prevSlug = prev ? docSlug(prev) : "";

    if (!shouldPushOnChange({ operation, wasPublished, prevSlug, slug })) return doc;

    const url = publicUrlFor(collection, slug);
    if (!url) return doc;

    void pushUrlsToIndexNow([url]).then((result) => {
      if (result.ok) {
        console.info(
          `[indexnow] ${collection}/${slug} ok status=${result.status}${result.message ? ` ${result.message}` : ""}`,
        );
      } else {
        console.warn(
          `[indexnow] ${collection}/${slug} fail: ${result.message || result.raw || result.status}`,
        );
      }
    });

    return doc;
  };
}
