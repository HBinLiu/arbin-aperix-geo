import type { SamplingPlatform } from "@/types/brand";

export type AnalysisEntityRef = {
  id: string;
  kind: "own" | "competitor";
  label: string;
  brand?: string | null;
  domain?: string;
  competitor_id: string | null;
};

export type AnalysisEntitiesData = {
  entities: AnalysisEntityRef[];
};

export type OverviewMetrics = {
  entity?: AnalysisEntityRef;
  window: { from: string; to: string };
  filters: { platforms: string[]; topic_id: string | null; entity_id?: string | null };
  visibility_rate: number | null;
  mention_rate: number | null;
  share_voice: number | null;
  average_rank: number | null;
  citation_rate: number | null;
  sentiment_score: number | null;
  citation_coverage: number | null;
};

/** 当前 / 上一周期数值对 */
export type MetricPeriod = {
  current: number | null;
  previous: number | null;
};

/** 带后端情感标签的指标周期（label: positive / neutral / negative） */
export type LabeledMetricPeriod = MetricPeriod & {
  label: string | null;
};

/** 概述页 KPI（含品牌排名位次，1 起） */
export type DashboardOverviewMetric = MetricPeriod & {
  rank: number | null;
};

export type DashboardOverviewSentimentMetric = DashboardOverviewMetric & {
  label: string | null;
};

export type DashboardOverviewRankRow = {
  id: string;
  label: string;
  domain: string;
  cur_value: number | null;
  pre_value: number | null;
};

export type DashboardOverviewTopic = {
  topic_id: string;
  topic_name: string;
  response_count: number;
  visibility: MetricPeriod;
  citation: MetricPeriod;
  sentiment: LabeledMetricPeriod;
  average_rank: MetricPeriod;
};

/** 控制台概述页统一数据（扁平结构） */
export type DashboardOverviewData = {
  entity_id: string;
  visibility: DashboardOverviewMetric;
  citation: DashboardOverviewMetric;
  share_voice: DashboardOverviewMetric;
  sentiment: DashboardOverviewSentimentMetric;
  visibility_chart: {
    cur_series: VisibilitySeriesPoint[];
    pre_series: VisibilitySeriesPoint[];
  };
  visibility_table: DashboardOverviewRankRow[];
  topic_table: DashboardOverviewTopic[];
};

export type RankBoardItem = {
  entity_id: string;
  label: string;
  brand?: string | null;
  domain: string;
  is_own: boolean;
  visibility_rate: number | null;
  mention_rate: number | null;
  share_voice: number | null;
  average_rank: number | null;
  citation_rate: number | null;
  sentiment_score: number | null;
  sentiment_label: string | null;
};

export type RankData = {
  own_label: string;
  items: RankBoardItem[];
};

export type PromptPerformance = {
  prompt_id: string;
  prompt_text: string;
  topic_id: string | null;
  topic_name: string | null;
  funnel_stage: string | null;
  search_intent: string | null;
  decision_type: string | null;
  visibility_rate: number | null;
  mention_rate: number | null;
  average_rank: number | null;
  citation_rate: number | null;
  sentiment_score: number | null;
  sentiment_label: string | null;
  response_count: number;
};

export type PromptPerformanceSortField =
  | "visibility_rate"
  | "mention_rate"
  | "average_rank"
  | "citation_rate"
  | "sentiment_score";

export type PromptPerformancePage = {
  items: PromptPerformance[];
  total: number;
  page: number;
  page_size: number;
};

export type TopicPerformance = {
  topic_id: string;
  topic_name: string;
  visibility_rate: number | null;
  mention_rate: number | null;
  average_rank: number | null;
  citation_rate: number | null;
  sentiment_score: number | null;
  sentiment_label: string | null;
  response_count: number;
};

export type PlatformPerformance = {
  platform: string;
  visibility_rate: number | null;
  mention_rate: number | null;
  share_voice: number | null;
  average_rank: number | null;
  citation_rate: number | null;
  sentiment_score: number | null;
  sentiment_label: string | null;
};

export type PlatformMatrixMetricId =
  | "visibility"
  | "shareVoice"
  | "citation"
  | "averageRank"
  | "sentiment";

export type PlatformMatrixRowDimension = "competitor" | "topic";

export type PlatformMatrixCell = {
  row_id: string;
  platform_id: string;
  visibility_rate: number | null;
  share_voice: number | null;
  citation_rate: number | null;
  average_rank: number | null;
  sentiment_score: number | null;
};

export type PlatformMatrixCells = {
  current: PlatformMatrixCell[];
  previous: PlatformMatrixCell[];
};

export type PlatformSeriesMetric =
  | "visibility"
  | "share_voice"
  | "citation"
  | "average_rank"
  | "sentiment";

export type PlatformChartSeriesPoint = {
  date: string;
  values: Record<string, number>;
};

export type PlatformChartWindow = {
  current: PlatformChartSeriesPoint[];
};

export type PlatformAnalysisData = {
  entity_id: string;
  matrix_row: PlatformMatrixRowDimension;
  matrix_cells: PlatformMatrixCells;
  performance: {
    current: PlatformPerformance[];
    previous: PlatformPerformance[];
  };
  charts: Record<PlatformSeriesMetric, PlatformChartWindow>;
};

/** @deprecated 使用 PlatformAnalysisData */
export type PlatformMatrixData = PlatformAnalysisData;

export type VisibilitySeriesPoint = {
  date: string;
  values: Record<string, number>;
};

export type VisibilityAnalysisData = {
  entity_id: string;
  visibility: DashboardOverviewMetric;
  mention: DashboardOverviewMetric;
  share_voice: DashboardOverviewMetric;
  average_rank: DashboardOverviewMetric;
  visibility_chart: {
    cur_series: VisibilitySeriesPoint[];
    pre_series: VisibilitySeriesPoint[];
  };
  mention_chart: {
    cur_series: VisibilitySeriesPoint[];
    pre_series: VisibilitySeriesPoint[];
  };
  average_rank_chart: {
    cur_series: { date: string; value: number | null }[];
    pre_series: { date: string; value: number | null }[];
  };
  visibility_table: DashboardOverviewRankRow[];
  mention_table: DashboardOverviewRankRow[];
  share_voice_table: DashboardOverviewRankRow[];
  average_rank_table: DashboardOverviewRankRow[];
  topic_visibility_ranks: {
    topic_id: string;
    topic_name: string;
    ranks: (string | null)[];
  }[];
};

export type CitationRankRow = {
  id: string;
  label: string;
  domain?: string | null;
  cur_value: number | null;
  pre_value: number | null;
};

export type CitationListPage<T> = {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  response_total?: number;
};

export type CitationDomainSortField = "count";
export type CitationUrlSortField = "count" | "citation_rate";

export type CitationDomainRow = {
  domain: string;
  count: number;
  platforms?: string[];
  citation_rate: number;
  monthly_visits: number | null;
};

export type CitationMentionedBrand = {
  label: string;
  brand?: string | null;
  domain: string | null;
};

export type CitationUrlCitingPrompt = {
  prompt_text: string;
  topic_name: string;
};

export type CitationUrlRow = {
  url: string;
  host: string;
  domain?: string;
  title: string;
  count: number;
  platforms?: string[];
  citation_rate: number;
  has_brand_analysis?: boolean;
  mentioned_brands: CitationMentionedBrand[];
  citing_prompts?: CitationUrlCitingPrompt[];
};

export type CitationAnalysisData = {
  entity_id: string;
  own_label: string;
  focus_label?: string;
  labels: string[];
  citation_rate: number | null;
  citation_previous: number | null;
  series: VisibilitySeriesPoint[];
  previous_series: VisibilitySeriesPoint[];
  rank_table: CitationRankRow[];
};

export type CitationDomainSeriesPoint = {
  date: string;
  count: number;
};

export type CitationDomainAnalysisData = {
  domain: string;
  count: number;
  citation_rate: number;
  prev_count: number;
  response_total: number;
  series: CitationDomainSeriesPoint[];
  previous_series: CitationDomainSeriesPoint[];
  topics: CitationDomainBreakdownRow[];
  platforms: CitationDomainBreakdownRow[];
};

export type CitationDomainPromptSortField = "count" | "citation_rate";

export type CitationDomainBreakdownRow = {
  id: string;
  name: string;
  topic_name?: string | null;
  platforms?: string[];
  count: number;
  citation_rate: number;
};

export type CitationDomainDetailTab = "pages" | "prompt" | "topic" | "platform";

export type CitationDetailTab = "domain" | "url";

export type SentimentDistributionPoint = {
  date: string;
  positive: number;
  neutral: number;
  negative: number;
  sentiment_score: number;
  sentiment_label: SentimentTab;
  /** 当日各平台平均情感分（chart tooltip） */
  platform_scores?: Record<string, number>;
};

export type SentimentRankRow = DashboardOverviewRankRow & {
  cur_label?: string | null;
};

export type PlatformSentimentPerformance = {
  platform_id: string;
  sentiment_score: number | null;
  sentiment_label: string | null;
};

export type AnalysisResponseRow = {
  response_id: string;
  platform_id: string;
  prompt_id: string;
  prompt_text: string;
  sentiment_score: number | null;
  sentiment_label: string | null;
  sentiment_reason?: string | null;
  reply_preview: string;
  created_at: string;
  mentioned?: boolean;
  rank?: number | null;
  mentioned_brands?: CitationMentionedBrand[];
  cited_on_source?: boolean;
};

export type AnalysisResponseSortField = "created_at" | "sentiment_score" | "rank";

export type AnalysisResponsesPage = {
  items: AnalysisResponseRow[];
  total: number;
  page: number;
  page_size: number;
};

export type SentimentAnalysisData = {
  entity_id: string;
  sentiment_score: number | null;
  sentiment_label: string | null;
  sentiment_previous: number | null;
  distribution_series: SentimentDistributionPoint[];
  rank_table: SentimentRankRow[];
};

export type SentimentTab = "positive" | "neutral" | "negative";

export type OpportunityPriority = "high" | "medium" | "low";

export type OpportunityTab = "backlink" | "competitor" | "social";

export type ContentOpportunityItem = {
  id: string;
  prompt_id: string;
  prompt_text: string;
  platforms: string[];
  priority: OpportunityPriority;
  mention_priority: OpportunityPriority;
  mention_rate: number;
  mention_own_count: number;
  mention_total_count: number;
  average_rank: number | null;
  mention_issue_type: DiagnosisIssueType;
  competitors: CitationMentionedBrand[];
  brand_gap_rate: number;
  brand_gap_priority: OpportunityPriority;
  brand_own_count: number;
  brand_total_count: number;
  source_gap_rate: number;
  source_gap_priority: OpportunityPriority;
  source_own_count: number;
  source_total_count: number;
};

export type ContentOpportunitySummary = {
  overall_score: number;
  overall_status: DiagnosisStatus;
  mention: DiagnosisDimensionSummary;
  brand_gap: DiagnosisDimensionSummary;
  source_gap: DiagnosisDimensionSummary;
};

export type DiagnosisContentListData = {
  entity_id: string;
  entity_label: string;
  items: ContentOpportunityItem[];
  total: number;
  page: number;
  page_size: number;
};

export type DiagnosisContentSummaryData = {
  entity_id: string;
  entity_label: string;
  summary: ContentOpportunitySummary;
};

/** @deprecated use DiagnosisContentListData */
export type ContentOpportunityData = DiagnosisContentListData & {
  summary?: ContentOpportunitySummary;
};

export type ContentOpportunitySortField =
  | "priority"
  | "brand_gap_rate"
  | "source_gap_rate"
  | "mention_rate";

export type ContentOpportunityDetailRow = {
  entity_id: string;
  /** 内部分析键（常为域名） */
  label: string;
  brand?: string | null;
  domain: string | null;
  platforms: string[];
  contribution_rate: number;
  average_rank: number | null;
  /** 来源差距：该竞品域名在相关回复中的引用链接 */
  citation_urls?: string[];
};

export type ContentOpportunityDetailBrand = {
  gap_rate: number;
  gap_priority: OpportunityPriority;
  chat_mention_own: number;
  chat_mention_total: number;
  /** 至少被提及一次的配置竞品数量 */
  competitor_brand_count: number;
  /** 配置品牌 mention_count 合计（含自有） */
  total_mention_count: number;
  rows: ContentOpportunityDetailRow[];
};

export type ContentOpportunityDetailSource = {
  gap_rate: number;
  gap_priority: OpportunityPriority;
  chat_source_own: number;
  chat_source_total: number;
  /** 至少在引用链接中出现域名的配置竞品数（去重域名） */
  competitor_source_count: number;
  /** 配置品牌引用链接命中累计次数（含自有，每回复每实体最多计 1） */
  total_source_count: number;
  rows: ContentOpportunityDetailRow[];
};

export type ContentOpportunityDetailData = {
  prompt_id: string;
  prompt_text: string;
  brand: ContentOpportunityDetailBrand;
  source: ContentOpportunityDetailSource;
};

export type ContentOpportunityDetailTab = "brand" | "source" | "chat";

export type BacklinkOpportunityItem = {
  id: string;
  domain: string;
  platforms: string[];
  priority: OpportunityPriority;
  citation_count: number;
  prompt_count: number;
  chat_count: number;
};

export type BacklinkOpportunityData = {
  items: BacklinkOpportunityItem[];
  total: number;
  page: number;
  page_size: number;
};

export type BacklinkOpportunitySortField = "priority" | "prompt_count" | "chat_count" | "citation_count";

export type BrandItem = {
  brand_id: string;
  label: string;
  brand?: string | null;
  domain: string;
  visibility_rate: number | null;
  mention_rate: number | null;
  share_voice: number | null;
  average_rank: number | null;
  citation_rate: number | null;
  sentiment_score: number | null;
  sentiment_label: string | null;
  response_count: number;
};

export type BrandData = {
  items: BrandItem[];
  total: number;
  page: number;
  page_size: number;
};

export type BrandSortField =
  | "visibility_rate"
  | "mention_rate"
  | "share_voice"
  | "average_rank"
  | "citation_rate"
  | "sentiment_score"
  | "brand";

export type BacklinkOpportunityDetailData = {
  domain: string;
  priority: OpportunityPriority;
  platforms: string[];
  citation_count: number;
  citation_rate: number;
  chat_count: number;
  prompt_count: number;
  mentioned_competitors: CitationMentionedBrand[];
};

export type BacklinkOpportunityUrlRow = CitationUrlRow & {
  platforms: string[];
};

export type BacklinkOpportunityDetailTab = "pages" | "prompt";

export type DiagnosisStatus = "excellent" | "good" | "improvement" | "critical";

export type DiagnosisIssueType = "not_mentioned" | "low_mention" | "poor_rank" | "healthy";

export type DiagnosisMentionItem = {
  id: string;
  prompt_id: string;
  prompt_text: string;
  platform: string;
  priority: OpportunityPriority;
  mention_rate: number;
  mention_own_count: number;
  mention_total_count: number;
  average_rank: number | null;
  issue_type: DiagnosisIssueType;
  competitors: string[];
};

export type DiagnosisDimensionSummary = {
  health_score: number;
  priority_counts: Record<OpportunityPriority, number>;
};

export type DiagnosisData = {
  overall_score: number;
  overall_status: DiagnosisStatus;
  dimensions: {
    mention: DiagnosisDimensionSummary;
  };
  mention_items: DiagnosisMentionItem[];
};

export type AnalysisQueryFilters = {
  entityId: string;
  platformIds: string[];
  topicIds: string[];
  from: string;
  to: string;
};

export type AnalysisFilters = {
  from: string;
  to: string;
  entityId: string;
  platformIds: string[];
  topicIds: string[];
};

export type AnalysisOutletContext = {
  subjectId: string;
};

export type LlmResponseDialogRow = {
  response_id: string;
  platform: string;
  reply_preview?: string;
};

export type PromptDetailResponseRow = LlmResponseDialogRow & {
  mentioned_brands: CitationMentionedBrand[];
  mentioned: boolean;
  rank: number | null;
  created_at: string;
  cited_on_source?: boolean;
};

export type PromptDetailSeriesPoint = {
  date: string;
  value: number | null;
};

export type PromptDetailPlatformRow = {
  platform: string;
  visibility_rate: number | null;
  average_rank: number | null;
  citation_rate: number | null;
};

export type PromptDetailOpportunityPayload = {
  brand_gap_rate: number;
  brand_gap_priority: OpportunityPriority;
  source_gap_rate: number;
  source_gap_priority: OpportunityPriority;
  mention_priority: OpportunityPriority;
  priority: OpportunityPriority;
};

export type PromptDetailData = {
  entity_id: string;
  entity_label: string;
  prompt_id: string;
  prompt_text: string;
  topic_id: string | null;
  topic_name: string | null;
  search_intent: string | null;
  visibility_rate: number | null;
  average_rank: number | null;
  citation_rate: number | null;
  visibility_series: PromptDetailSeriesPoint[];
  average_rank_series: PromptDetailSeriesPoint[];
  citation_series: PromptDetailSeriesPoint[];
  platforms: PromptDetailPlatformRow[];
  opportunity: PromptDetailOpportunityPayload | null;
  citation_responses: PromptDetailResponseRow[];
};

/** LLM 回复 parsed 字段（与后端 sampling parser 一致） */
export type AbsaBrandEntry = {
  mentioned?: boolean;
  score?: number | null;
  evidence?: string;
};

export type CitationResponseAbsa = {
  analysis_source?: string;
  brands_sentiment_absa?: Record<string, AbsaBrandEntry>;
  other_brands_sentiment_absa?: Record<string, AbsaBrandEntry>;
};

export type EntitySignalRecord = {
  entity_id: string;
  entity_kind: "own" | "competitor" | "other";
  entity_label: string;
  brand?: string | null;
  domain?: string | null;
  brand_id?: string | null;
  primary_domain?: string | null;
  match_terms?: string[];
  mentioned?: boolean;
  mention_count?: number;
  mention_rank?: number | null;
  sentiment_score?: number | null;
  sentiment_label?: string | null;
  sentiment_reason?: string | null;
  has_domain_link?: boolean;
  cited_on_source?: boolean;
};

export type LlmResponseParsed = {
  urls?: string[];
  url_hosts?: string[];
  source_urls_from_api?: string[];
  citation_urls_own?: string[];
  citation_sources?: unknown[];
  citation_response_absa?: CitationResponseAbsa;
  entity_signals?: EntitySignalRecord[];
  own_brand?: string;
  sentiment_source?: string;
  web_search_mode?: string;
};

export type LlmResponseDetail = {
  id: string;
  sampling_job_id: string;
  prompt_id: string;
  platform: string;
  status: string;
  error_text: string | null;
  raw_text: string;
  parsed: LlmResponseParsed | null;
  latency_ms: number | null;
  usage: unknown;
  created_at: string;
};
