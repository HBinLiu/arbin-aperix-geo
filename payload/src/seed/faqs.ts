import type { Faq } from "@shared/faq";
import {
  answerEngineInsightsFaqDefaults,
  contentCreationFaqDefaults,
  findTopicsIdeasFaqDefaults,
  homeFaqDefaults,
  monitorFaqDefaults,
  pricingFaqDefaults,
  promptExplorerFaqDefaults,
  singlePageAuditFaqDefaults,
  llmsTxtGeneratorFaqDefaults,
  hotPromptFinderFaqDefaults,
  geoWebsiteFaqDefaults,
  teamSolutionFaqDefaultsBySlug,
  sceneFaqDefaultsBySlug,
} from "@shared/faq/defaults";
import {
  FAQ_PAGE,
  FAQ_PAGE_LABEL_BY_VALUE,
  MONITOR_FAQ_SLUGS,
  TEAM_SOLUTION_SLUGS,
  SCENE_SLUGS,
  monitorFaqPage,
  teamSolutionFaqPage,
  sceneFaqPage,
  type FaqPageKey,
} from "@shared/faq/pages";

export type FaqSeedGroup = {
  page: FaqPageKey;
  label: string;
  items: Faq[];
};

/** 与 `shared/faq/defaults.ts` 对齐；监测页共用同一套默认 FAQ */
export const faqSeedGroups: FaqSeedGroup[] = [
  { page: FAQ_PAGE.home, label: FAQ_PAGE_LABEL_BY_VALUE[FAQ_PAGE.home], items: homeFaqDefaults },
  {
    page: FAQ_PAGE.pricing,
    label: FAQ_PAGE_LABEL_BY_VALUE[FAQ_PAGE.pricing],
    items: pricingFaqDefaults,
  },
  {
    page: FAQ_PAGE.platformAnswer,
    label: FAQ_PAGE_LABEL_BY_VALUE[FAQ_PAGE.platformAnswer],
    items: answerEngineInsightsFaqDefaults,
  },
  {
    page: FAQ_PAGE.platformTopics,
    label: FAQ_PAGE_LABEL_BY_VALUE[FAQ_PAGE.platformTopics],
    items: findTopicsIdeasFaqDefaults,
  },
  {
    page: FAQ_PAGE.platformPrompt,
    label: FAQ_PAGE_LABEL_BY_VALUE[FAQ_PAGE.platformPrompt],
    items: promptExplorerFaqDefaults,
  },
  {
    page: FAQ_PAGE.platformContent,
    label: FAQ_PAGE_LABEL_BY_VALUE[FAQ_PAGE.platformContent],
    items: contentCreationFaqDefaults,
  },
  {
    page: FAQ_PAGE.singlePageAudit,
    label: FAQ_PAGE_LABEL_BY_VALUE[FAQ_PAGE.singlePageAudit],
    items: singlePageAuditFaqDefaults,
  },
  {
    page: FAQ_PAGE.llmsTxtGenerator,
    label: FAQ_PAGE_LABEL_BY_VALUE[FAQ_PAGE.llmsTxtGenerator],
    items: llmsTxtGeneratorFaqDefaults,
  },
  {
    page: FAQ_PAGE.hotPromptFinder,
    label: FAQ_PAGE_LABEL_BY_VALUE[FAQ_PAGE.hotPromptFinder],
    items: hotPromptFinderFaqDefaults,
  },
  {
    page: FAQ_PAGE.geoWebsite,
    label: FAQ_PAGE_LABEL_BY_VALUE[FAQ_PAGE.geoWebsite],
    items: geoWebsiteFaqDefaults,
  },
  ...MONITOR_FAQ_SLUGS.map((slug) => {
    const page = monitorFaqPage(slug);
    return {
      page,
      label: FAQ_PAGE_LABEL_BY_VALUE[page],
      items: monitorFaqDefaults,
    };
  }),
  ...TEAM_SOLUTION_SLUGS.map((slug) => {
    const page = teamSolutionFaqPage(slug);
    return {
      page,
      label: FAQ_PAGE_LABEL_BY_VALUE[page],
      items: [...teamSolutionFaqDefaultsBySlug[slug]],
    };
  }),
  ...SCENE_SLUGS.map((slug) => {
    const page = sceneFaqPage(slug);
    return {
      page,
      label: FAQ_PAGE_LABEL_BY_VALUE[page],
      items: [...sceneFaqDefaultsBySlug[slug]],
    };
  }),
];

export function faqSeedCount(): number {
  return faqSeedGroups.reduce((total, group) => total + group.items.length, 0);
}

export function faqSeedPageCount(): number {
  return faqSeedGroups.length;
}
