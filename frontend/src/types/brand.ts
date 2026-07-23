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
  decision_type: string;
  enabled: boolean;
  parent_prompt_id?: string;
  kind?: "root" | "fanout" | string;
  origin_query?: string;
  created_at: string;
};

export type PromptTaxonomyOption = {
  value: string;
  label: string;
};

export type PromptTaxonomy = {
  funnel_stages: PromptTaxonomyOption[];
  search_intents: PromptTaxonomyOption[];
  decision_types: PromptTaxonomyOption[];
  default_funnel_stage: string;
  default_search_intent: string;
  default_decision_type: string;
};

export type CompetitorItem = {
  id?: string;
  domain: string;
  website_url: string;
  brand: string;
  summary: string;
  aliases?: string[];
};

export type CompetitorsData = {
  competitors: CompetitorItem[];
};

export type PromoteBrandData = {
  competitor: CompetitorItem;
  brand_id: string;
  entity_label: string;
  signals_migrated: number;
  signals_dropped: number;
};
