export type SubjectMode = "domain" | "brand";

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
};

export type DiscoveredCompetitor = {
  domain: string;
  website_url?: string;
  brand: string;
  summary: string;
};

export type CompetitorRow = {
  id: string;
  name: string;
  domain: string;
  summary: string;
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
  mode: SubjectMode;
  sessionId: string;
  domain: string;
  brand: string;
  region: string;
  language: string;
  topicRows: TopicRow[];
  competitorRows: CompetitorRow[];
  promptRows: PromptRow[];
};
