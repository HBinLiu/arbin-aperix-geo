import type { APIRoute } from "astro";
import { mergeHomeFaqs } from "@/lib/home";
import { buildLlmsTxt } from "@/lib/llms";
import { getHomeFaqs } from "@/lib/payload";
import { siteConfig } from "@site";

export const GET: APIRoute = async ({ site }) => {
  const origin = site ?? new URL(siteConfig.url);
  const faqs = mergeHomeFaqs(await getHomeFaqs());
  return new Response(buildLlmsTxt(origin, faqs), {
    headers: { "Content-Type": "text/plain; charset=utf-8" },
  });
};
