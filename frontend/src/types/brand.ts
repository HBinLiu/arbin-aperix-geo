export type SamplingPlatform = {
  platform: string;
  label: string;
};

export type SubjectTopic = {
  id: string;
  subject_id: string;
  name: string;
  created_at: string;
};

export type SubjectPrompt = {
  id: string;
  subject_id: string;
  topic_id: string;
  text: string;
  funnel_stage: string;
  search_intent: string;
  enabled: boolean;
  created_at: string;
};

export type CompetitorItem = {
  domain: string;
  website_url: string;
  brand: string;
  summary: string;
  aliases?: string[];
};

export type CompetitorsData = {
  competitors: CompetitorItem[];
};
