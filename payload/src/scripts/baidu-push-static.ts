/**
 * 从线上官网 /sitemap.xml 拉取 URL，推送到百度普通收录。
 *
 * 用法（在 payload 目录）：
 *   npm run baidu:push-static
 *   npm run baidu:push-all
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

/** payload run 会吃掉 npm 传来的 flag；用 `payload run … -- --all` 或独立 npm script */
const includeAll =
  process.argv.includes("--all") || process.env.BAIDU_PUSH_ALL === "1";

function log(message: string) {
  process.stderr.write(`${message}\n`);
}

async function main() {
  if (!isBaiduPushEnabled()) {
    log("未配置 BAIDU_PUSH_SITE / BAIDU_PUSH_TOKEN（请写入 .env.production 后重试）。");
    process.exit(1);
  }

  const base = getWebsiteUrl();
  if (!/^https:\/\//i.test(base)) {
    log(`PUBLIC_WEBSITE_URL 须为 https 公网地址，当前: ${base}`);
    process.exit(1);
  }

  const mode = includeAll ? "全部" : "营销";
  log(`[baidu-push] 从 ${base}/sitemap.xml 收集 ${mode} URL…`);

  let urls: string[];
  try {
    urls = includeAll
      ? await collectAllSitemapUrls(base)
      : await collectStaticSitemapUrls(base);
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    log(`[baidu-push] 拉取 sitemap 失败: ${message}`);
    process.exit(1);
  }

  if (urls.length === 0) {
    log("未解析到任何 URL（检查容器内能否访问 /sitemap.xml，以及官网 Node 是否已部署新路由）。");
    process.exit(1);
  }

  log(`[baidu-push] 共 ${urls.length} 条，开始推送…`);
  const summary = await pushUrlListToBaidu(urls);
  for (const [i, result] of summary.results.entries()) {
    if (result.ok) {
      log(
        `[baidu-push] batch ${i + 1}/${summary.batches} ok success=${result.success ?? "?"} remain=${result.remain ?? "?"}`,
      );
    } else {
      log(
        `[baidu-push] batch ${i + 1}/${summary.batches} fail: ${result.message || result.raw || result.status}`,
      );
    }
  }

  if (!summary.ok) process.exit(1);
  process.exit(0);
}

await main();
