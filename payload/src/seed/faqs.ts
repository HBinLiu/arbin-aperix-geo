import type { Faq } from "@shared/faq";
import {
  answerEngineInsightsFaqDefaults,
  contentCreationFaqDefaults,
  findTopicsIdeasFaqDefaults,
  homeFaqDefaults,
  monitorFaqDefaults,
  pricingFaqDefaults,
  promptExplorerFaqDefaults,
} from "@shared/faq/defaults";
import {
  FAQ_PAGE,
  FAQ_PAGE_LABEL_BY_VALUE,
  MONITOR_FAQ_SLUGS,
  monitorFaqPage,
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
  ...MONITOR_FAQ_SLUGS.map((slug) => {
    const page = monitorFaqPage(slug);
    return {
      page,
      label: FAQ_PAGE_LABEL_BY_VALUE[page],
      items: monitorFaqDefaults,
    };
  }),
];

export function faqSeedCount(): number {
  return faqSeedGroups.reduce((total, group) => total + group.items.length, 0);
}

export function faqSeedPageCount(): number {
  return faqSeedGroups.length;
}
