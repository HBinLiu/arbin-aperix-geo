import { authorHref } from "@/lib/blog";
import { getAllAuthorDocs } from "@/lib/payload";
import { createCmsSitemapHandler } from "@/lib/sitemap";

export const prerender = false;

export const GET = createCmsSitemapHandler({
  getDocs: getAllAuthorDocs,
  pathForDoc: (doc) => authorHref(doc.slug),
  lastmodForDoc: (doc) => doc.updatedAt,
});
