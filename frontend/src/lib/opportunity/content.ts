import type { CSSProperties } from "react";

import type { ContentOpportunityItem, OpportunityPriority } from "@/types";

export const CONTENT_OPPORTUNITY_TITLE = "内容机会";
export const CONTENT_OPPORTUNITY_DESCRIPTION =
  "识别竞品占优而自有品牌存在差距的提示词，将数据洞察转化为可执行的内容策略，助力品牌在 AI 搜索场景中实现增长。";

export const BACKLINK_OPPORTUNITY_TITLE = "反向链接机会";
export const BACKLINK_OPPORTUNITY_DESCRIPTION =
  "锁定 AI 模型信赖的高权重域名以暴露竞品优势缺口，并将外链建设资源集中在那些真正能带来可见度的关键链接上。";

export const SOCIAL_OPPORTUNITY_TITLE = "社交媒体机会";
export const SOCIAL_OPPORTUNITY_DESCRIPTION =
  "追踪 AI 提及与社媒声量的关联机会，拓展品牌在社交媒体平台的可见度。";

/** 机会表列宽：百分比布局（合计 100%），提示词列另有最小宽度 */
export type ContentOpportunityColumn = {
  id: "prompt" | "priority" | "platform" | "competitors" | "brandGap" | "sourceGap" | "action";
  width: string;
  minWidth: number;
};

export const CONTENT_OPPORTUNITY_COLUMNS: readonly ContentOpportunityColumn[] = [
  { id: "prompt", width: "36%", minWidth: 240 },
  { id: "priority", width: "10%", minWidth: 100 },
  { id: "platform", width: "12%", minWidth: 135 },
  { id: "competitors", width: "12%", minWidth: 135 },
  { id: "brandGap", width: "11%", minWidth: 120 },
  { id: "sourceGap", width: "11%", minWidth: 120 },
  { id: "action", width: "8%", minWidth: 60 },
];

/** 容器窄于此宽度时出现横向滚动 */
export const CONTENT_OPPORTUNITY_MIN_WIDTH = CONTENT_OPPORTUNITY_COLUMNS.reduce(
  (sum, column) => sum + column.minWidth,
  0,
);

/** 提示词列在 table-fixed 中可收缩并 truncate */
export function contentOpportunityPromptCellStyle(): CSSProperties {
  const prompt = CONTENT_OPPORTUNITY_COLUMNS[0];
  return {
    minWidth: prompt.minWidth,
    maxWidth: 0,
  };
}

export function contentOpportunityColumnColStyle(
  column: ContentOpportunityColumn,
): CSSProperties {
  return { width: column.width, minWidth: column.minWidth };
}

export type ContentOpportunityRow = {
  id: string;
  promptText: string;
  priority: OpportunityPriority;
  priorityLabel: string;
  platform: string;
  competitors: string[];
  brandGap: string;
  brandGapNum: number;
  brandGapSub: string;
  sourceGap: string;
  sourceGapNum: number;
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

function gapSubtext(own: number, total: number): string {
  return `${own}/${total} 条回复`;
}

export function buildContentOpportunityRows(items: ContentOpportunityItem[]): ContentOpportunityRow[] {
  return items.map((item) => ({
    id: item.id,
    promptText: item.prompt_text,
    priority: item.priority,
    priorityLabel: PRIORITY_LABELS[item.priority],
    platform: item.platform,
    competitors: item.competitors,
    brandGap: formatGapRate(item.brand_gap_rate),
    brandGapNum: item.brand_gap_rate,
    brandGapSub: gapSubtext(item.brand_own_count, item.brand_total_count),
    sourceGap: formatGapRate(item.source_gap_rate),
    sourceGapNum: item.source_gap_rate,
    sourceGapSub: gapSubtext(item.source_own_count, item.source_total_count),
  }));
}

export type ContentOpportunitySortColumn = "priority" | "brandGap" | "sourceGap";

export function sortContentOpportunityRows(
  rows: ContentOpportunityRow[],
  column: ContentOpportunitySortColumn,
  dir: "asc" | "desc",
): ContentOpportunityRow[] {
  const sign = dir === "asc" ? 1 : -1;

  const valueOf = (row: ContentOpportunityRow): number => {
    if (column === "priority") return PRIORITY_ORDER[row.priority];
    if (column === "brandGap") return row.brandGapNum;
    return row.sourceGapNum;
  };

  return [...rows].sort((a, b) => (valueOf(a) - valueOf(b)) * sign);
}

export function filterContentOpportunityRows(
  rows: ContentOpportunityRow[],
  search: string,
): ContentOpportunityRow[] {
  const query = search.trim().toLowerCase();
  if (!query) return rows;
  return rows.filter((row) => row.promptText.toLowerCase().includes(query));
}

export function gapTone(value: number): "high" | "medium" | "low" {
  if (value >= 0.8) return "high";
  if (value >= 0.5) return "medium";
  return "low";
}
