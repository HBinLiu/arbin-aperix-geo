import type { Endpoint } from "payload";

import { collectAllSitemapUrls, collectStaticSitemapUrls } from "../sitemap";
import { pushUrlListToIndexNow } from "./batch";
import { pushUrlsToIndexNow, isIndexNowPushEnabled } from "./client";

const INDEXNOW_MAX_REQUEST = 10_000;

/**
 * POST /cms/api/indexnow-push
 *
 * Body 任选其一：
 * - `{ "urls": ["https://…"] }` 手动指定
 * - `{ "sitemap": "static" }` 拉取 /sitemap.xml 中营销页（排除 CMS 路径）
 * - `{ "sitemap": "all" }` 拉取全站 /sitemap.xml（回填）
 *
 * 需已登录 CMS。
 */
export const indexNowPushEndpoint: Endpoint = {
  path: "/indexnow-push",
  method: "post",
  handler: async (req) => {
    if (!req.user) {
      return Response.json({ error: "Unauthorized" }, { status: 401 });
    }
    if (!isIndexNowPushEnabled()) {
      return Response.json({ error: "IndexNow 未配置（INDEXNOW_KEY）" }, { status: 503 });
    }

    let body: unknown;
    try {
      body = await req.json?.();
    } catch {
      return Response.json({ error: "Invalid JSON" }, { status: 400 });
    }

    const sitemapMode = (body as { sitemap?: unknown })?.sitemap;
    if (sitemapMode === "static" || sitemapMode === "all") {
      const urls =
        sitemapMode === "all"
          ? await collectAllSitemapUrls()
          : await collectStaticSitemapUrls();
      if (urls.length === 0) {
        return Response.json(
          { error: "未从 sitemap 解析到 URL（检查 PUBLIC_WEBSITE_URL 与 /sitemap.xml）" },
          { status: 502 },
        );
      }
      const summary = await pushUrlListToIndexNow(urls);
      return Response.json(summary, { status: summary.ok ? 200 : 502 });
    }

    const urls = Array.isArray((body as { urls?: unknown })?.urls)
      ? ((body as { urls: unknown[] }).urls.filter((item) => typeof item === "string") as string[])
      : [];

    if (urls.length === 0) {
      return Response.json(
        { error: '请传 urls，或 sitemap: "static" | "all"' },
        { status: 400 },
      );
    }
    if (urls.length > INDEXNOW_MAX_REQUEST) {
      return Response.json(
        { error: `单次最多 ${INDEXNOW_MAX_REQUEST} 条 URL` },
        { status: 400 },
      );
    }

    const result = await pushUrlsToIndexNow(urls);
    return Response.json(result, { status: result.ok ? 200 : 502 });
  },
};
