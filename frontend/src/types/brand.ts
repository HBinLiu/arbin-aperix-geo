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
  enabled: boolean;
  created_at: string;
};

export type CompetitorsData = {
  competitors: { domain: string; site_name: string }[];
  domains: string[];
  brand_names: string[];
};
