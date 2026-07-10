export type PlatformFaqItem = {
  number: string;
  label: string;
  question: string;
  paragraphs: string[];
  bullets?: string[];
  closingParagraphs?: string[];
};

export const platformFaqDefaults = {
  title: "常见问题",
  subtitle: "我们已整理了最关键的信息，以助您最大化您的体验价值。",
} as const;
