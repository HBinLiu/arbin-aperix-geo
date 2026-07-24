import { newsHref } from "@/lib/news";
import { getAllNewsDocs } from "@/lib/payload";
import { createCmsSitemapHandler } from "@/lib/sitemap";

export const prerender = false;

export const GET = createCmsSitemapHandler({
  listPath: "/news/",
  getDocs: getAllNewsDocs,
  pathForDoc: (doc) => newsHref(doc.slug),
  lastmodForDoc: (doc) => doc.publishedAt,
});
