import type { APIRoute } from "astro";

const getRobotsTxt = (sitemapURL: URL, llmsURL: URL) => `User-agent: *
Allow: /

Sitemap: ${sitemapURL.href}
# LLM site summary: ${llmsURL.href}
`;

export const GET: APIRoute = ({ site }) => {
  const sitemapURL = new URL("sitemap.xml", site);
  const llmsURL = new URL("llms.txt", site);
  return new Response(getRobotsTxt(sitemapURL, llmsURL), {
    headers: { "Content-Type": "text/plain; charset=utf-8" },
  });
};
