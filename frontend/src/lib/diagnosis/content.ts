import type { CSSProperties } from "react";

import type {
  CitationMentionedBrand,
  ContentOpportunityDetailTab,
  ContentOpportunityItem,
  ContentOpportunitySortField,
  ContentOpportunitySummary,
  OpportunityPriority,
} from "@/types";

/** 诊断表列宽：百分比布局（合计 100%），提示词列另有最小宽度 */
export type DiagnosisContentColumn = {
  id:
    | "prompt"
    | "priority"
    | "platform"
    | "competitors"
    | "mentionRate"
    | "brandGap"
    | "sourceGap"
    | "action";
  width: string;
  minWidth: number;
};

export const DIAGNOSIS_CONTENT_COLUMNS: readonly DiagnosisContentColumn[] = [
  { id: "prompt", width: "26%", minWidth: 200 },
  { id: "priority", width: "10%", minWidth: 100 },
  { id: "platform", width: "12%", minWidth: 120 },
  { id: "competitors", width: "12%", minWidth: 130 },
  { id: "mentionRate", width: "11%", minWidth: 110 },
  { id: "brandGap", width: "11%", minWidth: 110 },
  { id: "sourceGap", width: "10%", minWidth: 100 },
  { id: "action", width: "8%", minWidth: 80 },
];

/** 容器窄于此宽度时出现横向滚动 */
export const DIAGNOSIS_CONTENT_MIN_WIDTH = DIAGNOSIS_CONTENT_COLUMNS.reduce(
  (sum, column) => sum + column.minWidth,
  0,
);

/** 提示词列在 table-fixed 中可收缩并 truncate */
export function diagnosisContentPromptCellStyle(): CSSProperties {
  const prompt = DIAGNOSIS_CONTENT_COLUMNS[0];
  return {
    minWidth: prompt.minWidth,
    maxWidth: 0,
  };
}

export function diagnosisContentColumnColStyle(column: DiagnosisContentColumn): CSSProperties {
  return { width: column.width, minWidth: column.minWidth };
}

export type DiagnosisContentRow = {
  id: string;
  promptId: string;
  promptText: string;
  priority: OpportunityPriority;
  priorityLabel: string;
  mentionPriority: OpportunityPriority;
  mentionPriorityLabel: string;
  mentionRate: string;
  mentionRateNum: number;
  mentionSub: string;
  platforms: string[];
  competitors: CitationMentionedBrand[];
  brandGap: string;
  brandGapNum: number;
  brandGapPriority: OpportunityPriority;
  brandGapSub: string;
  sourceGap: string;
  sourceGapNum: number;
  sourceGapPriority: OpportunityPriority;
  sourceGapSub: string;
};

const PRIORITY_LABELS: Record<OpportunityPriority, string> = {
  high: "高",
  medium: "中",
  low: "低",
};

const PRIORITY_ORDER: Record<OpportunityPriority, number> = {
  high: 0,
  medium: 1,
  low: 2,
};

function formatGapRate(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}

function formatMentionRate(value: number): string {
  return `${(value * 100).toFixed(0)}%`;
}

export function gapReplySubtext(own: number, total: number): string {
  return `${own}/${total} 条回复`;
}

export function buildDiagnosisContentRows(items: ContentOpportunityItem[]): DiagnosisContentRow[] {
  return items.map((item) => ({
    id: item.id,
    promptId: item.prompt_id,
    promptText: item.prompt_text,
    priority: item.priority,
    priorityLabel: PRIORITY_LABELS[item.priority],
    mentionPriority: item.mention_priority,
    mentionPriorityLabel: PRIORITY_LABELS[item.mention_priority],
    mentionRate: formatMentionRate(item.mention_rate),
    mentionRateNum: item.mention_rate,
    mentionSub: gapReplySubtext(item.mention_own_count, item.mention_total_count),
    platforms: item.platforms,
    competitors: item.competitors.map((label) => ({ label, domain: null })),
    brandGap: formatGapRate(item.brand_gap_rate),
    brandGapNum: item.brand_gap_rate,
    brandGapPriority: item.brand_gap_priority,
    brandGapSub: gapReplySubtext(item.brand_own_count, item.brand_total_count),
    sourceGap: formatGapRate(item.source_gap_rate),
    sourceGapNum: item.source_gap_rate,
    sourceGapPriority: item.source_gap_priority,
    sourceGapSub: gapReplySubtext(item.source_own_count, item.source_total_count),
  }));
}

export type DiagnosisContentSortColumn = "priority" | "brandGap" | "sourceGap" | "mentionRate";

export function diagnosisContentSortToApiField(
  column: DiagnosisContentSortColumn,
  dir: "asc" | "desc",
): { sortBy: ContentOpportunitySortField; order: "asc" | "desc" } {
  const sortBy: ContentOpportunitySortField =
    column === "brandGap"
      ? "brand_gap_rate"
      : column === "sourceGap"
        ? "source_gap_rate"
        : column === "mentionRate"
          ? "mention_rate"
          : "priority";
  return { sortBy, order: dir };
}

export const DIAGNOSIS_CONTENT_DETAIL_TABS: {
  id: ContentOpportunityDetailTab;
  label: string;
}[] = [
  { id: "brand", label: "品牌差距" },
  { id: "source", label: "来源差距" },
  { id: "chat", label: "聊天" },
];

export function sortDiagnosisContentRows(
  rows: DiagnosisContentRow[],
  column: DiagnosisContentSortColumn,
  dir: "asc" | "desc",
): DiagnosisContentRow[] {
  const sign = dir === "asc" ? 1 : -1;

  const valueOf = (row: DiagnosisContentRow): number => {
    if (column === "priority") return PRIORITY_ORDER[row.priority];
    if (column === "brandGap") return row.brandGapNum;
    if (column === "sourceGap") return row.sourceGapNum;
    return row.mentionRateNum;
  };

  return [...rows].sort((a, b) => (valueOf(a) - valueOf(b)) * sign);
}

export function diagnosisContentOverview(summary: ContentOpportunitySummary | undefined) {
  if (!summary) {
    return {
      overallScore: 0,
      overallStatus: "critical" as const,
      mention: { health_score: 0, priority_counts: { high: 0, medium: 0, low: 0 } },
      brandGap: { health_score: 0, priority_counts: { high: 0, medium: 0, low: 0 } },
      sourceGap: { health_score: 0, priority_counts: { high: 0, medium: 0, low: 0 } },
    };
  }

  return {
    overallScore: summary.overall_score,
    overallStatus: summary.overall_status,
    mention: summary.mention,
    brandGap: summary.brand_gap,
    sourceGap: summary.source_gap,
  };
}
