export type OverviewMetrics = {
  window: { from: string; to: string };
  filters: { platforms: string[]; topic_id: string | null };
  visibility_rate: number | null;
  mention_intensity: number | null;
  share_voice: number | null;
  average_rank: number | null;
  citation_rate: number | null;
  sentiment_score: number | null;
  sentiment_count: { positive: number; neutral: number; negative: number };
  citation_coverage: number | null;
};

export type BrandRankData = {
  own_label: string;
  mention_counts: Record<string, number>;
  visibility_counts: Record<string, number>;
  visibility_share: Record<string, number>;
  mention_share: Record<string, number>;
  share_voice: Record<string, number>;
  average_rank: Record<string, number | null>;
  citation_share: Record<string, number>;
  sentiment_score: Record<string, number | null>;
};

export type RankData = BrandRankData;

export type PromptPerformance = {
  prompt_id: string;
  prompt_text: string;
  topic_id: string | null;
  topic_name: string | null;
  visibility_rate: number | null;
  mention_intensity: number | null;
  average_rank: number | null;
  citation_rate: number | null;
  sentiment_score: number | null;
  response_count: number;
};

export type TopicPerformance = {
  topic_id: string;
  topic_name: string;
  visibility_rate: number | null;
  mention_intensity: number | null;
  average_rank: number | null;
  citation_rate: number | null;
  sentiment_score: number | null;
  response_count: number;
};

export type PlatformPerformance = {
  platform: string;
  visibility_rate: number | null;
  mention_intensity: number | null;
  share_voice: number | null;
  average_rank: number | null;
  citation_rate: number | null;
  sentiment_score: number | null;
};

export type PlatformMatrixMetricId =
  | "visibility"
  | "shareVoice"
  | "citation"
  | "averageRank"
  | "sentiment";

export type PlatformMatrixRowDimension = "competitor" | "topic";

export type PlatformMatrixSeriesPoint = {
  date: string;
  value: number | null;
};

export type PlatformMatrixData = {
  own_label: string;
  platforms: string[];
  competitor_rows: { id: string; label: string; is_own: boolean }[];
  topic_rows: { id: string; label: string }[];
  competitor_values: Record<
    "visibility" | "share_voice" | "citation" | "average_rank" | "sentiment",
    Record<string, Record<string, number | null>>
  >;
  topic_values: Record<
    "visibility" | "share_voice" | "citation" | "average_rank" | "sentiment",
    Record<string, Record<string, number | null>>
  >;
  platform_performance: PlatformPerformance[];
  platform_series: Record<
    string,
    Record<
      "visibility" | "share_voice" | "citation" | "average_rank" | "sentiment",
      PlatformMatrixSeriesPoint[]
    >
  >;
};

export type VisibilitySeriesPoint = {
  date: string;
  values: Record<string, number>;
};

export type VisibilityAnalysisData = {
  own_label: string;
  labels: string[];
  share_voice_labels: string[];
  rank: BrandRankData;
  series: VisibilitySeriesPoint[];
  mention_series: VisibilitySeriesPoint[];
  average_rank_series: { date: string; value: number | null }[];
  previous_rank: BrandRankData;
  previous_series: VisibilitySeriesPoint[];
  previous_mention_series: VisibilitySeriesPoint[];
  previous_average_rank_series: { date: string; value: number | null }[];
  topic_visibility_ranks: {
    topic_id: string;
    topic_name: string;
    ranks: (string | null)[];
  }[];
};

export type CitationRankData = {
  own_label: string;
  citation_counts: Record<string, number>;
  citation_share: Record<string, number>;
};

export type CitationDomainRow = {
  host: string;
  count: number;
  citation_rate: number;
  monthly_visits: number | null;
  domain_type: string | null;
};

export type CitationUrlRow = {
  url: string;
  count: number;
  citation_rate: number;
};

export type CitationAnalysisData = {
  own_label: string;
  labels: string[];
  citation_rate: number | null;
  rank: CitationRankData;
  previous_rank: CitationRankData;
  series: VisibilitySeriesPoint[];
  previous_series: VisibilitySeriesPoint[];
  domains: CitationDomainRow[];
  urls: CitationUrlRow[];
};

export type CitationDetailTab = "domain" | "url";

export type DailySentimentSeries = {
  own_label: string;
  series: { date: string; value: number | null }[];
};

export type SentimentDistributionPoint = {
  date: string;
  positive: number;
  neutral: number;
  negative: number;
};

export type SentimentResponseRow = {
  response_id: string;
  platform: string;
  prompt_id: string;
  prompt_text: string;
  sentiment: "positive" | "neutral" | "negative" | string;
  sentiment_score: number | null;
  reply_preview: string;
  created_at: string;
};

export type SentimentAnalysisData = {
  own_label: string;
  sentiment_score: number | null;
  sentiment_count: { positive: number; neutral: number; negative: number };
  distribution_series: SentimentDistributionPoint[];
  platform_performance: PlatformPerformance[];
  previous_platform_performance: PlatformPerformance[];
  responses: SentimentResponseRow[];
};

export type SentimentTab = "positive" | "neutral" | "negative";

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
