/** Lexical BlocksFeature slug（Payload block slug 与 HTML converter key 共用） */
export const CONTENT_BLOCK_SLUGS = {
  brief: "brief",
  callout: "callout",
  figure: "figure",
  highlight: "highlight",
  infoGrid: "infoGrid",
  chapter: "chapter",
  inlineCta: "inlineCta",
} as const;

export type ContentBlockSlug = (typeof CONTENT_BLOCK_SLUGS)[keyof typeof CONTENT_BLOCK_SLUGS];

export type BriefBlockFields = {
  anchorId?: string | null;
  eyebrow?: string | null;
  title: string;
  items: Array<{
    lead?: string | null;
    body?: string | null;
  }>;
};

export type CalloutBlockFields = {
  lead: string;
  body?: string | null;
};

export type FigureBlockFields = {
  image: string | { url?: string | null; alt?: string | null; width?: number | null; height?: number | null };
  alt?: string | null;
  caption?: string | null;
};

export type HighlightBlockFields = {
  label: string;
  body: string;
};

export type InfoGridBlockFields = {
  anchorId?: string | null;
  title?: string | null;
  paragraphs?: Array<{
    text: string;
  }> | null;
  cards: Array<{
    label?: string | null;
    title: string;
    description?: string | null;
  }>;
};

export type ChapterBlockFields = {
  text: string;
};

export type InlineCtaBlockFields = {
  kicker?: string | null;
  title: string;
  description: string;
  buttonLabel: string;
  /** AppLinkKey：register | login */
  buttonHref: string;
};
