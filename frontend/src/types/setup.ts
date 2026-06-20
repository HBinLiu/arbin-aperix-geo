export type SubjectMode = "domain" | "brand";

export type GeneratedPromptItem = {
  text: string;
  funnel_stage: string;
  search_intent: string;
};

export type TopicRow = {
  id: string;
  name: string;
  selected: boolean;
};

export type PromptRow = {
  id: string;
  text: string;
  topicId: string;
  selected: boolean;
  /** 仅用于 finalize 落库，Setup UI 不展示 */
  funnelStage?: string;
  searchIntent?: string;
};

export type DiscoveredCompetitor = {
  domain: string;
  website_url?: string;
  brand: string;
};

export type CompetitorRow = {
  id: string;
  name: string;
  domain: string;
  websiteUrl: string;
  summary: string;
  aliases: string[];
  selected: boolean;
};

export type SetupCache = {
  sessionId: string;
  mode: SubjectMode;
  websiteUrl: string;
  brandName: string;
  region: string;
  language: string;
  topicRows: TopicRow[];
  competitorRows: CompetitorRow[];
  promptRows: PromptRow[];
  step: number;
};

export type FinalizeSetupInput = {
  sessionId: string;
  topicRows: TopicRow[];
  promptRows: PromptRow[];
};
