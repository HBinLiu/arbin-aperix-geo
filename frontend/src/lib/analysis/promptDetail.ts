import { formatRank, formatRate } from "@/lib/analysis/format";
import type { SingleSeriesPoint } from "@/lib/analysis/chart";
import type {
  ContentOpportunityItem,
  OpportunityPriority,
  PlatformPerformance,
  PromptDetailResponseRow,
  PromptPerformance,
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
    chartDescription: "品牌在此提示词的 AI 生成答案中出现的频率",
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
    description: "在此提示词下，提及品牌且引用自有域名链接的回复占比。反映内容可信度和将 AI 浏览量转化为网站流量的能力。比率越高表示被引用的内容越广泛。",
    chartDescription: "品牌在此提示词下您的域名引用百分比",
    formatValue: formatRate,
    yAxisMode: "rate",
  },
];

export type PromptOpportunitySummary = {
  brandGapRate: number;
  brandOwnCount: number;
  brandTotalCount: number;
  sourceGapRate: number;
  sourceOwnCount: number;
  sourceTotalCount: number;
  priority: OpportunityPriority;
};

const PRIORITY_LABELS: Record<OpportunityPriority, string> = {
  high: "高优先级",
  medium: "中优先级",
  low: "低优先级",
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

function opportunityPriority(brandGap: number, sourceGap: number): OpportunityPriority {
  const peak = Math.max(brandGap, sourceGap);
  if (peak >= 0.8) return "high";
  if (peak >= 0.5) return "medium";
  return "low";
}

export function aggregatePromptOpportunity(
  items: ContentOpportunityItem[],
): PromptOpportunitySummary | null {
  if (items.length === 0) return null;

  const brandOwnCount = items.reduce((sum, item) => sum + item.brand_own_count, 0);
  const brandTotalCount = items.reduce((sum, item) => sum + item.brand_total_count, 0);
  const sourceOwnCount = items.reduce((sum, item) => sum + item.source_own_count, 0);
  const sourceTotalCount = items.reduce((sum, item) => sum + item.source_total_count, 0);

  const brandGapRate =
    brandTotalCount > 0 ? Math.max(0, 1 - brandOwnCount / brandTotalCount) : 0;
  const sourceGapRate =
    sourceTotalCount > 0 ? Math.max(0, 1 - sourceOwnCount / sourceTotalCount) : 0;

  return {
    brandGapRate,
    brandOwnCount,
    brandTotalCount,
    sourceGapRate,
    sourceOwnCount,
    sourceTotalCount,
    priority: opportunityPriority(brandGapRate, sourceGapRate),
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
    chat_responses: PromptDetailResponseRow[];
    citation_responses: PromptDetailResponseRow[];
  } | null | undefined,
  tab: PromptDetailResponseTab,
): PromptDetailResponseRow[] {
  if (!data) return [];
  if (tab === "chat") return data.chat_responses;
  if (tab === "citation") return data.citation_responses;
  return [];
}
