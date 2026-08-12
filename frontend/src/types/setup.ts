export type SubjectMode = "domain" | "brand";

export type GeneratedPromptItem = {
  text: string;
  funnel_stage: string;
  search_intent: string;
  decision_type?: string;
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
  funnelStage?: string;
  searchIntent?: string;
  decisionType?: string;
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

export type SetupUploadFile = {
  id: string;
  name: string;
  mime: string;
  size: number;
  status: string;
};

export type SetupCache = {
  sessionId: string;
  mode: SubjectMode;
  websiteUrl: string;
  brandName: string;
  brandIntro: string;
  brandWebsiteUrl: string;
  uploadFiles: SetupUploadFile[];
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
