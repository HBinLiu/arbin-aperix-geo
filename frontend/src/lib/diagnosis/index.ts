import type { CSSProperties } from "react";

import type {
  DiagnosisData,
  DiagnosisIssueType,
  DiagnosisMentionItem,
  DiagnosisPromptItem,
  DiagnosisStatus,
  OpportunityPriority,
} from "@/types";

export const DIAGNOSIS_TABS = [
  { id: "mention" as const, label: "AI提及与平均排名" },
  { id: "prompt" as const, label: "提示词" },
];

export const DIAGNOSIS_PRIORITY_FILTER_OPTIONS = [
  { id: "all", label: "所有行动优先级" },
  { id: "high", label: "高" },
  { id: "medium", label: "中" },
  { id: "low", label: "低" },
] as const;

export type DiagnosisTab = (typeof DIAGNOSIS_TABS)[number]["id"];
export type DiagnosisPriorityFilter = (typeof DIAGNOSIS_PRIORITY_FILTER_OPTIONS)[number]["id"];

export const DIAGNOSIS_STATUS_LABELS: Record<DiagnosisStatus, string> = {
  excellent: "优秀",
  good: "良好",
  needs_improvement: "待改善",
  critical: "亟需改善",
};

export const ISSUE_TYPE_LABELS: Record<DiagnosisIssueType, string> = {
  not_mentioned: "完全未被提及",
  low_mention: "提及不足",
  poor_rank: "排名靠后",
  healthy: "表现良好",
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

export type DiagnosisMentionRow = {
  id: string;
  promptText: string;
  priority: OpportunityPriority;
  priorityLabel: string;
  mentionRate: string;
  mentionRateNum: number;
  mentionSub: string;
  issueType: DiagnosisIssueType;
  issueLabel: string;
  platform: string;
  competitors: string[];
};

export type DiagnosisPromptRow = {
  id: string;
  promptText: string;
  priority: OpportunityPriority;
  priorityLabel: string;
  mentionRate: string;
  mentionRateNum: number;
  mentionSub: string;
  issueType: DiagnosisIssueType;
  issueLabel: string;
};

export type DiagnosisMentionColumn = {
  id: "prompt" | "priority" | "mentionRate" | "issueType" | "platform" | "competitors" | "action";
  width: string;
  minWidth: number;
};

export const DIAGNOSIS_MENTION_COLUMNS: readonly DiagnosisMentionColumn[] = [
  { id: "prompt", width: "26%", minWidth: 200 },
  { id: "priority", width: "10%", minWidth: 88 },
  { id: "mentionRate", width: "12%", minWidth: 108 },
  { id: "issueType", width: "14%", minWidth: 120 },
  { id: "platform", width: "10%", minWidth: 88 },
  { id: "competitors", width: "12%", minWidth: 108 },
  { id: "action", width: "8%", minWidth: 72 },
];

export const DIAGNOSIS_MENTION_MIN_WIDTH = DIAGNOSIS_MENTION_COLUMNS.reduce(
  (sum, column) => sum + column.minWidth,
  0,
);

export const DIAGNOSIS_PROMPT_COLUMNS = [
  { id: "prompt", width: "38%", minWidth: 220 },
  { id: "priority", width: "12%", minWidth: 96 },
  { id: "mentionRate", width: "14%", minWidth: 108 },
  { id: "issueType", width: "16%", minWidth: 120 },
  { id: "action", width: "8%", minWidth: 72 },
] as const;

export const DIAGNOSIS_PROMPT_MIN_WIDTH = DIAGNOSIS_PROMPT_COLUMNS.reduce(
  (sum, column) => sum + column.minWidth,
  0,
);

export function diagnosisPromptCellStyle(minWidth: number): CSSProperties {
  return { minWidth, maxWidth: 0 };
}

export function diagnosisColumnColStyle(column: { width: string; minWidth: number }): CSSProperties {
  return { width: column.width, minWidth: column.minWidth };
}

function formatRate(value: number): string {
  return `${(value * 100).toFixed(0)}%`;
}

function mentionSubtext(own: number, total: number): string {
  return `${own}/${total} 条回复`;
}

function mapMentionItem(item: DiagnosisMentionItem): DiagnosisMentionRow {
  return {
    id: item.id,
    promptText: item.prompt_text,
    priority: item.priority,
    priorityLabel: PRIORITY_LABELS[item.priority],
    mentionRate: formatRate(item.mention_rate),
    mentionRateNum: item.mention_rate,
    mentionSub: mentionSubtext(item.mention_own_count, item.mention_total_count),
    issueType: item.issue_type,
    issueLabel: ISSUE_TYPE_LABELS[item.issue_type],
    platform: item.platform,
    competitors: item.competitors,
  };
}

function mapPromptItem(item: DiagnosisPromptItem): DiagnosisPromptRow {
  return {
    id: item.id,
    promptText: item.prompt_text,
    priority: item.priority,
    priorityLabel: PRIORITY_LABELS[item.priority],
    mentionRate: formatRate(item.mention_rate),
    mentionRateNum: item.mention_rate,
    mentionSub: mentionSubtext(item.mention_own_count, item.mention_total_count),
    issueType: item.issue_type,
    issueLabel: ISSUE_TYPE_LABELS[item.issue_type],
  };
}

export function buildDiagnosisMentionRows(items: DiagnosisMentionItem[]): DiagnosisMentionRow[] {
  return items.map(mapMentionItem);
}

export function buildDiagnosisPromptRows(items: DiagnosisPromptItem[]): DiagnosisPromptRow[] {
  return items.map(mapPromptItem);
}

export type DiagnosisMentionSortColumn = "priority" | "mentionRate";

export function sortDiagnosisMentionRows(
  rows: DiagnosisMentionRow[],
  column: DiagnosisMentionSortColumn,
  dir: "asc" | "desc",
): DiagnosisMentionRow[] {
  const sign = dir === "asc" ? 1 : -1;
  const valueOf = (row: DiagnosisMentionRow): number => {
    if (column === "priority") return PRIORITY_ORDER[row.priority];
    return row.mentionRateNum;
  };
  return [...rows].sort((a, b) => (valueOf(a) - valueOf(b)) * sign);
}

export type DiagnosisPromptSortColumn = "priority" | "mentionRate";

export function sortDiagnosisPromptRows(
  rows: DiagnosisPromptRow[],
  column: DiagnosisPromptSortColumn,
  dir: "asc" | "desc",
): DiagnosisPromptRow[] {
  const sign = dir === "asc" ? 1 : -1;
  const valueOf = (row: DiagnosisPromptRow): number => {
    if (column === "priority") return PRIORITY_ORDER[row.priority];
    return row.mentionRateNum;
  };
  return [...rows].sort((a, b) => (valueOf(a) - valueOf(b)) * sign);
}

export function filterDiagnosisByPriority<T extends { priority: OpportunityPriority }>(
  rows: T[],
  filter: DiagnosisPriorityFilter,
): T[] {
  if (filter === "all") return rows;
  return rows.filter((row) => row.priority === filter);
}

export function diagnosisOverview(data: DiagnosisData | undefined) {
  return {
    overallScore: data?.overall_score ?? 0,
    overallStatus: data?.overall_status ?? "critical",
    mention: data?.dimensions.mention ?? { health_score: 0, priority_counts: { high: 0, medium: 0, low: 0 } },
    prompt: data?.dimensions.prompt ?? { health_score: 0, priority_counts: { high: 0, medium: 0, low: 0 } },
  };
}

export function mentionRateTone(value: number): "high" | "medium" | "low" {
  if (value <= 0) return "high";
  if (value < 0.5) return "medium";
  return "low";
}

export function issueTypeDotClass(issueType: DiagnosisIssueType): string {
  if (issueType === "not_mentioned") return "bg-red-500";
  if (issueType === "low_mention" || issueType === "poor_rank") return "bg-amber-500";
  return "bg-emerald-500";
}
