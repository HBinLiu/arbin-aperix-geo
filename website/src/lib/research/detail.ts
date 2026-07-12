import {
  buildResearchHeroFallback,
  researchSidebarDefault,
  type ResearchHeroDetail,
  type ResearchListItem,
  type ResearchSidebarCta,
  type ResearchTocItem,
} from "@shared/research";
import type { CmsResearchDoc } from "@/lib/research/types";
import { researchRichTextToHtml } from "@/lib/research/body";
import { extractResearchToc } from "@/lib/research/toc";
import { resolveSiteCopyDeep } from "@/lib/site";

export type ResearchDetailViewModel = {
  listItem: ResearchListItem;
  hero: ResearchHeroDetail;
  sidebar: ResearchSidebarCta;
  toc: ResearchTocItem[];
  bodyHtml: string;
  hasBody: boolean;
};

function resolveResearchHero(_slug: string, listItem: ResearchListItem): ResearchHeroDetail {
  return buildResearchHeroFallback(listItem.slug, listItem.cardTitle, listItem.cardDescription);
}

function resolveResearchSidebar(_slug: string): ResearchSidebarCta {
  return researchSidebarDefault;
}

export function buildResearchDetail(
  listItem: ResearchListItem,
  cmsDoc: CmsResearchDoc | null | undefined,
): ResearchDetailViewModel {
  const body = cmsDoc?.body ?? null;
  const bodyHtml = researchRichTextToHtml(body);
  const hasBody = bodyHtml.trim().length > 0;

  return resolveSiteCopyDeep({
    listItem,
    hero: resolveResearchHero(listItem.slug, listItem),
    sidebar: resolveResearchSidebar(listItem.slug),
    toc: extractResearchToc(body),
    bodyHtml,
    hasBody,
  });
}
