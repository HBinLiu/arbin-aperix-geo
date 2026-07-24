import { blogHref } from "@/lib/blog";
import { getAllBlogDocs } from "@/lib/payload";
import { createCmsSitemapHandler } from "@/lib/sitemap";

export const prerender = false;

export const GET = createCmsSitemapHandler({
  listPath: "/blog/",
  getDocs: getAllBlogDocs,
  pathForDoc: (doc) => blogHref(doc.slug),
  lastmodForDoc: (doc) => doc.updatedAt ?? doc.publishedAt,
});
