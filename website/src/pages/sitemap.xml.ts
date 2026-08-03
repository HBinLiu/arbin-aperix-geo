import type { APIRoute } from "astro";

import {
  buildUrlsetXml,
  collectSiteSitemapEntries,
  sitemapXmlResponse,
} from "@/lib/sitemap";

export const prerender = false;

/** 全站单一 urlset：营销页 + CMS 详情，百度 / Google 均可提交 */
export const GET: APIRoute = async ({ site }) => {
  const origin = (site?.origin ?? "").replace(/\/$/, "");
  if (!origin) {
    return new Response("Missing site origin", { status: 500 });
  }

  const entries = await collectSiteSitemapEntries(origin);
  return sitemapXmlResponse(buildUrlsetXml(entries));
};
