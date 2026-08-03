import type { Endpoint } from "payload";

import { pushUrlsToBaidu, isBaiduPushEnabled } from "../lib/baiduPush";
import {
  collectAllSitemapUrls,
  collectStaticSitemapUrls,
  pushUrlListToBaidu,
} from "../lib/baiduPushSitemap";

/**
 * POST /cms/api/baidu-push
 *
 * Body 任选其一：
 * - `{ "urls": ["https://…"] }` 手动指定
 * - `{ "sitemap": "static" }` 拉取 /sitemap.xml 中营销页（排除 CMS 路径）
 * - `{ "sitemap": "all" }` 拉取全站 /sitemap.xml（回填）
 *
 * 需已登录 CMS。
 */
export const baiduPushEndpoint: Endpoint = {
  path: "/baidu-push",
  method: "post",
  handler: async (req) => {
    if (!req.user) {
      return Response.json({ error: "Unauthorized" }, { status: 401 });
    }
    if (!isBaiduPushEnabled()) {
      return Response.json(
        { error: "百度推送未配置（BAIDU_PUSH_SITE / BAIDU_PUSH_TOKEN）" },
        { status: 503 },
      );
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
      const summary = await pushUrlListToBaidu(urls);
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
    if (urls.length > 2000) {
      return Response.json({ error: "单次最多 2000 条 URL" }, { status: 400 });
    }

    const result = await pushUrlsToBaidu(urls);
    return Response.json(result, { status: result.ok ? 200 : 502 });
  },
};
