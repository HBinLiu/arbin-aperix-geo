import type { APIRoute } from "astro";
import { mergeHomeFaqs } from "@/lib/home";
import { buildLlmsTxt } from "@/lib/llms";
import { getFaqsByPage } from "@/lib/payload";
import { FAQ_PAGE } from "@shared/faq/pages";
import { siteConfig } from "@site";

export const GET: APIRoute = async ({ site }) => {
  const origin = site ?? new URL(siteConfig.url);
  const faqs = mergeHomeFaqs(await getFaqsByPage(FAQ_PAGE.home));
  return new Response(buildLlmsTxt(origin, faqs), {
    headers: { "Content-Type": "text/plain; charset=utf-8" },
  });
};
