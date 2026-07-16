/** Lexical BlocksFeature slug（Payload block slug 与 HTML converter key 共用） */
export const ACADEMY_BLOCK_SLUGS = {
  brief: "academyBrief",
  callout: "academyCallout",
  figure: "academyFigure",
  highlight: "academyHighlight",
  infoGrid: "academyInfoGrid",
  lead: "academyLead",
  inlineCta: "academyInlineCta",
} as const;

export type AcademyBlockSlug = (typeof ACADEMY_BLOCK_SLUGS)[keyof typeof ACADEMY_BLOCK_SLUGS];

export type AcademyBriefBlockFields = {
  anchorId?: string | null;
  eyebrow?: string | null;
  title: string;
  items: Array<{
    lead: string;
    body?: string | null;
  }>;
};

export type AcademyCalloutBlockFields = {
  lead: string;
  body?: string | null;
};

export type AcademyFigureBlockFields = {
  image: string | { url?: string | null; alt?: string | null; width?: number | null; height?: number | null };
  alt?: string | null;
  caption?: string | null;
};

export type AcademyHighlightBlockFields = {
  label: string;
  body: string;
};

export type AcademyInfoGridBlockFields = {
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

export type AcademyLeadBlockFields = {
  text: string;
};

export type AcademyInlineCtaBlockFields = {
  kicker?: string | null;
  title: string;
  description: string;
  buttonLabel: string;
  /** AppLinkKey：register | login */
  buttonHref: string;
};
