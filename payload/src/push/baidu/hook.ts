import type { CollectionAfterChangeHook, CollectionSlug } from "payload";

import { pushUrlsToBaidu, isBaiduPushEnabled } from "./client";
import {
  docSlug,
  isPublished,
  publicUrlFor,
  shouldPushOnChange,
} from "../paths";

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

    if (!shouldPushOnChange({ operation, wasPublished, prevSlug, slug })) return doc;

    const url = publicUrlFor(collection, slug);
    if (!url) return doc;

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
