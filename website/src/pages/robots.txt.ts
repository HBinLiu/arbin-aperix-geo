import type { APIRoute } from "astro";
import { DYNAMIC_SITEMAP_PATHS } from "@/lib/sitemap";

const getRobotsTxt = (sitemapLines: string[], llmsURL: URL) => `User-agent: *
Allow: /

${sitemapLines.join("\n")}
# LLM site summary: ${llmsURL.href}
`;

export const GET: APIRoute = ({ site }) => {
  const sitemapLines = [
    `Sitemap: ${new URL("sitemap-index.xml", site).href}`,
    ...DYNAMIC_SITEMAP_PATHS.map((path) => `Sitemap: ${new URL(path, site).href}`),
  ];
  const llmsURL = new URL("llms.txt", site);
  return new Response(getRobotsTxt(sitemapLines, llmsURL), {
    headers: { "Content-Type": "text/plain; charset=utf-8" },
  });
};
