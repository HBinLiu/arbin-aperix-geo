/** Lexical BlocksFeature slug（Payload block slug 与 HTML converter key 共用） */
export const BLOG_BLOCK_SLUGS = {
  brief: "blogBrief",
  callout: "blogCallout",
  figure: "blogFigure",
  highlight: "blogHighlight",
  infoGrid: "blogInfoGrid",
  lead: "blogLead",
  inlineCta: "blogInlineCta",
} as const;

export type BlogBlockSlug = (typeof BLOG_BLOCK_SLUGS)[keyof typeof BLOG_BLOCK_SLUGS];

export type BlogBriefBlockFields = {
  anchorId?: string | null;
  eyebrow?: string | null;
  title: string;
  items: Array<{
    lead: string;
    body?: string | null;
  }>;
};

export type BlogCalloutBlockFields = {
  lead: string;
  body?: string | null;
};

export type BlogFigureBlockFields = {
  image: string | { url?: string | null; alt?: string | null; width?: number | null; height?: number | null };
  alt?: string | null;
  caption?: string | null;
};

export type BlogHighlightBlockFields = {
  label: string;
  body: string;
};

export type BlogInfoGridBlockFields = {
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

export type BlogLeadBlockFields = {
  text: string;
};

export type BlogInlineCtaBlockFields = {
  kicker?: string | null;
  title: string;
  description: string;
  buttonLabel: string;
  /** AppLinkKey：register | login */
  buttonHref: string;
};
