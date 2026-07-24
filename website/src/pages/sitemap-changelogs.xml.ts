import { changelogHref } from "@/lib/changelog";
import { getAllChangelogDocs } from "@/lib/payload";
import { createCmsSitemapHandler } from "@/lib/sitemap";

export const prerender = false;

export const GET = createCmsSitemapHandler({
  listPath: "/changelogs/",
  getDocs: getAllChangelogDocs,
  pathForDoc: (doc) => changelogHref(doc.slug),
  lastmodForDoc: (doc) => doc.updatedAt ?? doc.publishedAt,
});
