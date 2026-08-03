/**
 * 从线上官网 /sitemap.xml 拉取 URL，推送到百度普通收录。
 *
 * 用法（在 payload 目录，需已配置 BAIDU_PUSH_* 与 PUBLIC_WEBSITE_URL=https://…）：
 *   npm run baidu:push-static          # 仅营销页（排除 /blog /academy 等 CMS 路径）
 *   npm run baidu:push-static -- --all # 全站 sitemap.xml
 *
 * 会显式加载 `.env` / `.env.production`（`payload run` 默认不读 production 文件）。
 */
import { loadEnvFiles } from "../lib/loadEnvFiles";
import {
  collectAllSitemapUrls,
  collectStaticSitemapUrls,
  pushUrlListToBaidu,
} from "../lib/baiduPushSitemap";
import { isBaiduPushEnabled } from "../lib/baiduPush";
import { getWebsiteUrl } from "../lib/urls";

loadEnvFiles();

const includeAll = process.argv.includes("--all");

async function main() {
  if (!isBaiduPushEnabled()) {
    console.error(
      "未配置 BAIDU_PUSH_SITE / BAIDU_PUSH_TOKEN（请写入 .env.production 或注入容器环境后重试）。",
    );
    process.exit(1);
  }

  const base = getWebsiteUrl();
  if (!/^https:\/\//i.test(base)) {
    console.error(`PUBLIC_WEBSITE_URL 须为 https 公网地址，当前: ${base}`);
    process.exit(1);
  }

  console.info(`[baidu-push] 从 ${base}/sitemap.xml 收集 ${includeAll ? "全部" : "营销"} URL…`);
  const urls = includeAll
    ? await collectAllSitemapUrls(base)
    : await collectStaticSitemapUrls(base);

  if (urls.length === 0) {
    console.error("未解析到任何 URL（检查 /sitemap.xml 是否可访问）。");
    process.exit(1);
  }

  console.info(`[baidu-push] 共 ${urls.length} 条，开始推送…`);
  const summary = await pushUrlListToBaidu(urls);
  for (const [i, result] of summary.results.entries()) {
    if (result.ok) {
      console.info(
        `[baidu-push] batch ${i + 1}/${summary.batches} ok success=${result.success ?? "?"} remain=${result.remain ?? "?"}`,
      );
    } else {
      console.warn(
        `[baidu-push] batch ${i + 1}/${summary.batches} fail: ${result.message || result.raw || result.status}`,
      );
    }
  }

  if (!summary.ok) process.exit(1);
}

void main();
