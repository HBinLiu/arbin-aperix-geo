import { getWebsiteUrl } from "../lib/urls";

/** 与 website CMS 栏目路径前缀对齐 */
const CMS_PATH_PREFIXES = [
  "/blog/",
  "/academy/",
  "/research/",
  "/news/",
  "/changelogs/",
  "/authors/",
] as const;

export function parseSitemapLocs(xml: string): string[] {
  const locs: string[] = [];
  const re = /<loc>\s*([^<\s]+)\s*<\/loc>/gi;
  let match: RegExpExecArray | null;
  while ((match = re.exec(xml)) !== null) {
    const loc = match[1]?.trim();
    if (loc && /^https?:\/\//i.test(loc)) locs.push(loc);
  }
  return locs;
}

function isCmsUrl(url: string): boolean {
  try {
    const path = new URL(url).pathname;
    // 列表页 /blog/ 等仍算「栏目」；静态推送时一并排除，由 --all / CMS hook 覆盖详情
    return CMS_PATH_PREFIXES.some(
      (prefix) => path === prefix.slice(0, -1) || path === prefix || path.startsWith(prefix),
    );
  } catch {
    return false;
  }
}

async function fetchUnifiedSitemapLocs(websiteBase: string): Promise<string[]> {
  const base = websiteBase.replace(/\/$/, "");
  try {
    const res = await fetch(`${base}/sitemap.xml`, { signal: AbortSignal.timeout(60_000) });
    if (!res.ok) return [];
    const xml = await res.text();
    if (/<sitemapindex[\s>]/i.test(xml)) return [];
    return [...new Set(parseSitemapLocs(xml))];
  } catch {
    return [];
  }
}

/** 营销静态页（排除 CMS 栏目路径） */
export async function collectStaticSitemapUrls(
  websiteBase = getWebsiteUrl(),
): Promise<string[]> {
  const all = await fetchUnifiedSitemapLocs(websiteBase);
  return all.filter((url) => !isCmsUrl(url));
}

/** 全站 sitemap.xml */
export async function collectAllSitemapUrls(
  websiteBase = getWebsiteUrl(),
): Promise<string[]> {
  return fetchUnifiedSitemapLocs(websiteBase);
}
