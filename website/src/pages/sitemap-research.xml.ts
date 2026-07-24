import { getAllResearchDocs } from "@/lib/payload";
import { researchHref } from "@/lib/research";
import { createCmsSitemapHandler } from "@/lib/sitemap";

export const prerender = false;

export const GET = createCmsSitemapHandler({
  listPath: "/research/",
  getDocs: getAllResearchDocs,
  pathForDoc: (doc) => researchHref(doc.slug),
  lastmodForDoc: (doc) => doc.publishedAt,
});
