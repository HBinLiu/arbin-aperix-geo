import { academyHref } from "@/lib/academy";
import { authorHref, blogHref } from "@/lib/blog";
import { changelogHref } from "@/lib/changelog";
import { newsHref } from "@/lib/news";
import {
  getAllAcademyDocs,
  getAllAuthorDocs,
  getAllBlogDocs,
  getAllChangelogDocs,
  getAllNewsDocs,
  getAllResearchDocs,
} from "@/lib/payload";
import { getAllMonitorPages, monitorHref } from "@/lib/platform/monitor";
import { researchHref } from "@/lib/research";
import { getAllScenePages } from "@/lib/scene/pages";
import { getAllTeamSolutionPages } from "@/lib/solution/team";

export type SitemapUrlEntry = {
  loc: string;
  lastmod?: string | null;
};

/** CMS 详情 / 列表路径前缀（百度「仅静态」推送时用于过滤） */
export const CMS_SITEMAP_PATH_PREFIXES = [
  "/blog",
  "/academy",
  "/research",
  "/news",
  "/changelogs",
  "/authors",
] as const;

function escapeXml(value: string): string {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&apos;");
}

function toLastmod(value: string | null | undefined): string | undefined {
  if (!value) return undefined;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return undefined;
  return date.toISOString();
}

export function withTrailingSlash(path: string): string {
  if (!path || path === "/") return "/";
  const normalized = path.startsWith("/") ? path : `/${path}`;
  return normalized.endsWith("/") ? normalized : `${normalized}/`;
}

/** 组装 sitemap urlset XML */
export function buildUrlsetXml(entries: SitemapUrlEntry[]): string {
  const urls = entries
    .map((entry) => {
      const lastmod = toLastmod(entry.lastmod ?? undefined);
      return [
        "  <url>",
        `    <loc>${escapeXml(entry.loc)}</loc>`,
        lastmod ? `    <lastmod>${lastmod}</lastmod>` : null,
        "  </url>",
      ]
        .filter(Boolean)
        .join("\n");
    })
    .join("\n");

  return `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${urls}
</urlset>
`;
}

export function sitemapXmlResponse(xml: string): Response {
  return new Response(xml, {
    headers: {
      "Content-Type": "application/xml; charset=utf-8",
      // 含 CMS 查询；短缓存降低爬虫打满 Payload
      "Cache-Control": "public, max-age=300",
    },
  });
}

export function absoluteUrl(origin: string, path: string): string {
  const base = origin.replace(/\/$/, "");
  return `${base}${withTrailingSlash(path)}`;
}

export function isCmsSitemapPath(pageUrl: string): boolean {
  try {
    const path = new URL(pageUrl).pathname.replace(/\/$/, "") || "/";
    return CMS_SITEMAP_PATH_PREFIXES.some(
      (prefix) => path === prefix || path.startsWith(`${prefix}/`),
    );
  } catch {
    return false;
  }
}

/** 营销 / 工具等代码内页面（不含 CMS 详情） */
export function getMarketingSitemapPaths(): string[] {
  const fixed = [
    "/",
    "/about/",
    "/contact/",
    "/pricing/",
    "/blog/",
    "/academy/",
    "/research/",
    "/news/",
    "/changelogs/",
    "/platform/answer-engine-insights/",
    "/platform/content-creation-optimization/",
    "/platform/find-topics-ideas/",
    "/platform/prompt-volumes-explorer/",
    "/free-tools/hot-prompt-finder/",
    "/free-tools/llms-txt-generator/",
    "/free-tools/single-page-audit/",
  ];

  const monitors = getAllMonitorPages().map((page) =>
    withTrailingSlash(monitorHref(page.platformId)),
  );
  const solutions = getAllTeamSolutionPages().map((page) =>
    withTrailingSlash(`/solution/${page.slug}`),
  );
  const scenes = getAllScenePages().map((page) => withTrailingSlash(`/scene/${page.slug}`));

  return [...new Set([...fixed, ...monitors, ...solutions, ...scenes])];
}

function dedupeEntries(entries: SitemapUrlEntry[]): SitemapUrlEntry[] {
  const byLoc = new Map<string, SitemapUrlEntry>();
  for (const entry of entries) {
    const existing = byLoc.get(entry.loc);
    if (!existing) {
      byLoc.set(entry.loc, entry);
      continue;
    }
    if (!existing.lastmod && entry.lastmod) {
      byLoc.set(entry.loc, entry);
    }
  }
  return [...byLoc.values()].sort((a, b) => a.loc.localeCompare(b.loc));
}

/** 全站 urlset：营销静态页 + CMS 已发布详情（请求时聚合） */
export async function collectSiteSitemapEntries(origin: string): Promise<SitemapUrlEntry[]> {
  const base = origin.replace(/\/$/, "");
  const marketing = getMarketingSitemapPaths().map((path) => ({
    loc: absoluteUrl(base, path),
  }));

  const [blogs, academies, researches, news, changelogs, authors] = await Promise.all([
    getAllBlogDocs(),
    getAllAcademyDocs(),
    getAllResearchDocs(),
    getAllNewsDocs(),
    getAllChangelogDocs(),
    getAllAuthorDocs(),
  ]);

  const cms: SitemapUrlEntry[] = [
    ...blogs.map((doc) => ({
      loc: absoluteUrl(base, blogHref(doc.slug)),
      lastmod: doc.updatedAt ?? doc.publishedAt,
    })),
    ...academies.map((doc) => ({
      loc: absoluteUrl(base, academyHref(doc.slug)),
      lastmod: doc.updatedAt ?? doc.publishedAt,
    })),
    ...researches.map((doc) => ({
      loc: absoluteUrl(base, researchHref(doc.slug)),
      lastmod: doc.publishedAt,
    })),
    ...news.map((doc) => ({
      loc: absoluteUrl(base, newsHref(doc.slug)),
      lastmod: doc.publishedAt,
    })),
    ...changelogs.map((doc) => ({
      loc: absoluteUrl(base, changelogHref(doc.slug)),
      lastmod: doc.updatedAt ?? doc.publishedAt,
    })),
    ...authors.map((doc) => ({
      loc: absoluteUrl(base, authorHref(doc.slug)),
      lastmod: doc.updatedAt,
    })),
  ];

  return dedupeEntries([...marketing, ...cms]);
}
