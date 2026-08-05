/**
 * 从线上官网 /sitemap.xml 拉取 URL，推送到 IndexNow。
 *
 * 用法（在 payload 目录）：
 *   npm run indexnow:push-static
 *   npm run indexnow:push-all
 *
 * 会显式加载 `.env` / `.env.production`（`payload run` 默认不读 production 文件）。
 */
import { loadEnvFiles } from "../../lib/loadEnvFiles";
import { getWebsiteUrl } from "../../lib/urls";
import { collectAllSitemapUrls, collectStaticSitemapUrls } from "../sitemap";
import { pushUrlListToIndexNow } from "./batch";
import { isIndexNowPushEnabled } from "./client";

loadEnvFiles();

const includeAll =
  process.argv.includes("--all") || process.env.INDEXNOW_PUSH_ALL === "1";

function log(message: string) {
  process.stderr.write(`${message}\n`);
}

async function main() {
  if (!isIndexNowPushEnabled()) {
    log("未配置 INDEXNOW_KEY（请写入 .env.production 后重试；须与官网 public/{key}.txt 一致）。");
    process.exit(1);
  }

  const base = getWebsiteUrl();
  if (!/^https:\/\//i.test(base)) {
    log(`PUBLIC_WEBSITE_URL 须为 https 公网地址，当前: ${base}`);
    process.exit(1);
  }

  const mode = includeAll ? "全部" : "营销";
  log(`[indexnow] 从 ${base}/sitemap.xml 收集 ${mode} URL…`);

  let urls: string[];
  try {
    urls = includeAll
      ? await collectAllSitemapUrls(base)
      : await collectStaticSitemapUrls(base);
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    log(`[indexnow] 拉取 sitemap 失败: ${message}`);
    process.exit(1);
  }

  if (urls.length === 0) {
    log("未解析到任何 URL（检查容器内能否访问 /sitemap.xml，以及官网 Node 是否已部署新路由）。");
    process.exit(1);
  }

  log(`[indexnow] 共 ${urls.length} 条，开始推送…`);
  const summary = await pushUrlListToIndexNow(urls);
  for (const [i, result] of summary.results.entries()) {
    if (result.ok) {
      log(
        `[indexnow] batch ${i + 1}/${summary.batches} ok status=${result.status}${result.message ? ` ${result.message}` : ""}`,
      );
    } else {
      log(
        `[indexnow] batch ${i + 1}/${summary.batches} fail: ${result.message || result.raw || result.status}`,
      );
    }
  }

  if (!summary.ok) process.exit(1);
  process.exit(0);
}

await main();
