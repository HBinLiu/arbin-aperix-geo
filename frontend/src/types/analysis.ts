export type OverviewMetrics = {
  window: { from: string; to: string };
  filters: { platforms: string[]; topic_id: string | null };
  response_count: number;
  visibility_rate: number | null;
  mention_intensity: number | null;
  share_of_voice: number | null;
  average_rank: number | null;
  citation_rate: number | null;
  sentiment_score: number | null;
  sentiment_own_counts: { positive: number; neutral: number; negative: number };
  citation_coverage: number | null;
};

export type RankData = {
  own_label: string;
  response_count: number;
  mention_counts: Record<string, number>;
  visibility_counts: Record<string, number>;
  visibility_share: Record<string, number>;
  share_of_voice: Record<string, number>;
};

export type PromptPerformance = {
  prompt_id: string;
  prompt_text: string;
  response_count: number;
  visibility_rate: number | null;
  mention_intensity: number | null;
  average_rank: number | null;
  last_sentiment: string | null;
};

export type PlatformPerformance = {
  platform: string;
  response_count: number;
  visibility_rate: number | null;
  mention_intensity: number | null;
  citation_rate: number | null;
  sentiment_score: number | null;
};

export type DailyVisibilitySeries = {
  own_label: string;
  labels: string[];
  series: { date: string; values: Record<string, number>; response_count: number }[];
};

export type CitationRankData = {
  own_label: string;
  response_count: number;
  citation_counts: Record<string, number>;
  citation_share: Record<string, number>;
};

export type DailySentimentSeries = {
  own_label: string;
  series: { date: string; value: number | null; response_count: number }[];
};

export type CitationsData = {
  subject_type: string;
  url_host_counts: { host: string; count: number }[];
  citation_coverage: number | null;
  citation_rate: number | null;
};

export type AnalysisQueryFilters = {
  regionId: string;
  topicId: string;
  platformId: string;
};

export type AnalysisFilters = AnalysisQueryFilters & {
  days: string;
};

export type AnalysisOutletContext = {
  subjectId: string;
};
