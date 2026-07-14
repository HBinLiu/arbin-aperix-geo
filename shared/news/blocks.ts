/** Lexical BlocksFeature slug（Payload block slug 与 HTML converter key 共用） */
export const NEWS_BLOCK_SLUGS = {
  brief: "newsBrief",
  callout: "newsCallout",
  figure: "newsFigure",
  highlight: "newsHighlight",
  infoGrid: "newsInfoGrid",
  lead: "newsLead",
  inlineCta: "newsInlineCta",
} as const;

export type NewsBlockSlug = (typeof NEWS_BLOCK_SLUGS)[keyof typeof NEWS_BLOCK_SLUGS];

export type NewsBriefBlockFields = {
  anchorId?: string | null;
  eyebrow?: string | null;
  title: string;
  items: Array<{
    lead: string;
    body?: string | null;
  }>;
};

export type NewsCalloutBlockFields = {
  lead: string;
  body?: string | null;
};

export type NewsFigureBlockFields = {
  image: string | { url?: string | null; alt?: string | null; width?: number | null; height?: number | null };
  alt?: string | null;
  caption?: string | null;
};

export type NewsHighlightBlockFields = {
  label: string;
  body: string;
};

export type NewsInfoGridBlockFields = {
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

export type NewsLeadBlockFields = {
  text: string;
};

export type NewsInlineCtaBlockFields = {
  kicker?: string | null;
  title: string;
  description: string;
  buttonLabel: string;
  /** AppLinkKey：register | login */
  buttonHref: string;
};
