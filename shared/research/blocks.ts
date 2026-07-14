/** Lexical BlocksFeature slug（Payload block slug 与 HTML converter key 共用） */
export const RESEARCH_BLOCK_SLUGS = {
  figure: "researchFigure",
  callout: "researchCallout",
  lead: "researchLead",
  inlineCta: "researchInlineCta",
} as const;

export type ResearchBlockSlug = (typeof RESEARCH_BLOCK_SLUGS)[keyof typeof RESEARCH_BLOCK_SLUGS];

export type ResearchFigureBlockFields = {
  image: string | { url?: string | null; alt?: string | null; width?: number | null; height?: number | null };
  alt?: string | null;
  caption?: string | null;
};

export type ResearchCalloutBlockFields = {
  label: string;
  body: string;
};

export type ResearchLeadBlockFields = {
  text: string;
};

export type ResearchInlineCtaBlockFields = {
  kicker?: string | null;
  title: string;
  description: string;
  buttonLabel: string;
  /** AppLinkKey：register | login */
  buttonHref: string;
};
