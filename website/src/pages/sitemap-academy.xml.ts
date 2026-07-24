import { academyHref } from "@/lib/academy";
import { getAllAcademyDocs } from "@/lib/payload";
import { createCmsSitemapHandler } from "@/lib/sitemap";

export const prerender = false;

export const GET = createCmsSitemapHandler({
  listPath: "/academy/",
  getDocs: getAllAcademyDocs,
  pathForDoc: (doc) => academyHref(doc.slug),
  lastmodForDoc: (doc) => doc.updatedAt ?? doc.publishedAt,
});
