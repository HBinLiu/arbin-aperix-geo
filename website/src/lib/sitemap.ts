import type { APIRoute } from "astro";

export type SitemapUrlEntry = {
  loc: string;
  lastmod?: string | null;
};

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
      "Cache-Control": "public, max-age=60",
    },
  });
}

export function absoluteUrl(origin: string, path: string): string {
  const base = origin.replace(/\/$/, "");
  const normalized = path.startsWith("/") ? path : `/${path}`;
  return `${base}${normalized}`;
}

type CmsSitemapConfig<T> = {
  /** 列表页路径；无独立列表时可省略 */
  listPath?: string;
  getDocs: () => Promise<T[]>;
  pathForDoc: (doc: T) => string;
  lastmodForDoc?: (doc: T) => string | null | undefined;
};

/** 动态 CMS sitemap：可选列表 URL + 各详情 slug */
export function createCmsSitemapHandler<T>(config: CmsSitemapConfig<T>): APIRoute {
  return async ({ site }) => {
    const origin = (site?.origin ?? "").replace(/\/$/, "");
    if (!origin) {
      return new Response("Missing site origin", { status: 500 });
    }

    const docs = await config.getDocs();
    const entries: SitemapUrlEntry[] = [
      ...(config.listPath ? [{ loc: absoluteUrl(origin, config.listPath) }] : []),
      ...docs.map((doc) => ({
        loc: absoluteUrl(origin, config.pathForDoc(doc)),
        lastmod: config.lastmodForDoc?.(doc),
      })),
    ];

    return sitemapXmlResponse(buildUrlsetXml(entries));
  };
}

/** 静态 @astrojs/sitemap 需排除的 CMS 路径前缀（避免陈旧详情 URL） */
export const CMS_SITEMAP_PATH_PREFIXES = [
  "/blog",
  "/academy",
  "/research",
  "/news",
  "/changelogs",
  "/authors",
] as const;

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

export const DYNAMIC_SITEMAP_PATHS = [
  "/sitemap-blog.xml",
  "/sitemap-academy.xml",
  "/sitemap-research.xml",
  "/sitemap-news.xml",
  "/sitemap-changelogs.xml",
  "/sitemap-authors.xml",
] as const;
