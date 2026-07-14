import {
  buildResearchHeroFallback,
  researchSidebarDefault,
  type ResearchHeroDetail,
  type ResearchListItem,
  type ResearchSidebarCta,
  type ResearchTocItem,
} from "@shared/research";
import { resolveAppLink } from "@/lib/app-links";
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

function normalizeCardLabels(labels: string[] | null | undefined): string[] {
  if (!labels?.length) return [];
  return labels.map((label) => label.trim()).filter(Boolean);
}

function resolveResearchHero(
  _slug: string,
  listItem: ResearchListItem,
  cmsDoc: CmsResearchDoc | null | undefined,
): ResearchHeroDetail {
  const hero = buildResearchHeroFallback(
    listItem.slug,
    listItem.cardTitle,
    listItem.cardDescription,
    normalizeCardLabels(cmsDoc?.cardLabels),
  );
  return {
    ...hero,
    actions: hero.actions.map((action) => ({
      ...action,
      href: resolveAppLink(action.href),
    })),
  };
}

function resolveResearchSidebar(_slug: string): ResearchSidebarCta {
  return {
    ...researchSidebarDefault,
    primaryHref: resolveAppLink(researchSidebarDefault.primaryHref),
    secondaryHref: resolveAppLink(researchSidebarDefault.secondaryHref),
  };
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
    hero: resolveResearchHero(listItem.slug, listItem, cmsDoc),
    sidebar: resolveResearchSidebar(listItem.slug),
    toc: extractResearchToc(body),
    bodyHtml,
    hasBody,
  });
}
