import { formatRank, formatRate } from "@/lib/analysis/format";
import type { SingleSeriesPoint } from "@/lib/analysis/chart";
import type {
  ContentOpportunityItem,
  OpportunityPriority,
  PlatformPerformance,
  PromptDetailResponseRow,
  PromptPerformance,
  AnalysisResponseRow,
  VisibilitySeriesPoint,
} from "@/types";

export type PromptDetailMetricId = "visibility" | "averageRank" | "citation";

export type PromptDetailMetricDefinition = {
  id: PromptDetailMetricId;
  label: string;
  description: string;
  chartDescription: string;
  formatValue: (value: number | null | undefined) => string;
  yAxisMode: "rate" | "score";
};

export const PROMPT_DETAIL_METRICS: PromptDetailMetricDefinition[] = [
  {
    id: "visibility",
    label: "可见度",
    description: "在此提示词下，提及您品牌的 AI 回复总数百分比。数值越高表示在所选平台中的曝光度和竞争可见度越高。",
    chartDescription: "品牌在此提示词 AI 回答中出现的频率",
    formatValue: formatRate,
    yAxisMode: "rate",
  },
  {
    id: "averageRank",
    label: "平均排名",
    description: "在此提示词下，品牌在 AI 推荐列表中的平均排名。反映在 AI 系统中的优先级。排名越高（数字越小）确保立即可见度。",
    chartDescription: "品牌在此提示词 AI 回答中的平均排名",
    formatValue: formatRank,
    yAxisMode: "score",
  },
  {
    id: "citation",
    label: "引用率",
    description: "在此提示词下，提及品牌且引用品牌域名链接的回复占比。反映内容可信度和将 AI 浏览量转化为网站流量的能力。比率越高表示被引用的内容越广泛。",
    chartDescription: "品牌在此提示词下品牌域名被引用百分比",
    formatValue: formatRate,
    yAxisMode: "rate",
  },
];

export type PromptOpportunitySummary = {
  brandGapRate: number;
  sourceGapRate: number;
  priority: OpportunityPriority;
};

const PRIORITY_LABELS: Record<OpportunityPriority, string> = {
  high: "高优先级",
  medium: "中优先级",
  low: "低优先级",
};

const PRIORITY_ORDER: Record<OpportunityPriority, number> = {
  high: 0,
  medium: 1,
  low: 2,
};

export function promptOpportunityPriorityLabel(priority: OpportunityPriority): string {
  return PRIORITY_LABELS[priority];
}

export function promptDetailMetric(
  id: PromptDetailMetricId,
): PromptDetailMetricDefinition {
  const metric = PROMPT_DETAIL_METRICS.find((item) => item.id === id);
  if (!metric) {
    throw new Error(`Unknown prompt detail metric: ${id}`);
  }
  return metric;
}

export function promptPerformanceSummary(
  rows: PromptPerformance[],
  promptId: string,
): PromptPerformance | undefined {
  return rows.find((row) => row.prompt_id === promptId);
}

export function extractOwnShareSeries(
  series: VisibilitySeriesPoint[],
  ownLabel: string,
): SingleSeriesPoint[] {
  if (!ownLabel) return [];
  return series.map((point) => ({
    date: point.date,
    value: point.values[ownLabel] ?? null,
  }));
}

export function platformMetricValue(
  row: PlatformPerformance,
  metricId: PromptDetailMetricId,
): number | null {
  switch (metricId) {
    case "visibility":
      return row.visibility_rate;
    case "averageRank":
      return row.average_rank;
    case "citation":
      return row.citation_rate;
  }
}

function highestOpportunityPriority(
  a: OpportunityPriority,
  b: OpportunityPriority,
): OpportunityPriority {
  return PRIORITY_ORDER[a] <= PRIORITY_ORDER[b] ? a : b;
}

export function aggregatePromptOpportunity(
  items: ContentOpportunityItem[],
): PromptOpportunitySummary | null {
  if (items.length === 0) return null;

  const brandGapRate = Math.max(0, ...items.map((item) => item.brand_gap_rate));
  const sourceGapRate = Math.max(0, ...items.map((item) => item.source_gap_rate));

  const brandGapPriority = items.reduce(
    (best, item) => highestOpportunityPriority(best, item.brand_gap_priority),
    "low" as OpportunityPriority,
  );
  const sourceGapPriority = items.reduce(
    (best, item) => highestOpportunityPriority(best, item.source_gap_priority),
    "low" as OpportunityPriority,
  );

  return {
    brandGapRate,
    sourceGapRate,
    priority: highestOpportunityPriority(brandGapPriority, sourceGapPriority),
  };
}

export function formatPromptGapRate(value: number): string {
  return `${(value * 100).toFixed(1)}% Gap`;
}

export type PromptDetailResponseTab = "chat" | "citation" | "queryExpansion";

export const PROMPT_DETAIL_RESPONSE_TABS: {
  id: PromptDetailResponseTab;
  label: string;
  help?: string;
}[] = [
  { id: "chat", label: "聊天" },
  { id: "citation", label: "引用率" },
  {
    id: "queryExpansion",
    label: "查询扩展",
    help: "AI 在回答前展开的子问题与查询变体，用于衡量提示词深度覆盖。",
  },
];

export function promptDetailResponsesForTab(
  data: {
    citation_responses: PromptDetailResponseRow[];
  } | null | undefined,
  tab: PromptDetailResponseTab,
  chatResponses: PromptDetailResponseRow[] = [],
): PromptDetailResponseRow[] {
  if (tab === "chat") return chatResponses;
  if (!data) return [];
  if (tab === "citation") return data.citation_responses;
  return [];
}

export function promptDetailResponseFromAnalysis(row: AnalysisResponseRow): PromptDetailResponseRow {
  return {
    response_id: row.response_id,
    platform: row.platform_id,
    reply_preview: row.reply_preview,
    mentioned_brands: row.mentioned_brands ?? [],
    mentioned: row.mentioned ?? false,
    rank: row.rank ?? null,
    created_at: row.created_at,
    cited_on_source: row.cited_on_source,
  };
}
