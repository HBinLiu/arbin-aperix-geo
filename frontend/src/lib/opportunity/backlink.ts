import type { CSSProperties } from "react";

import type { BacklinkOpportunityItem, OpportunityPriority } from "@/types";

export type BacklinkOpportunityColumn = {
  id: "domain" | "priority" | "domainType" | "platform" | "promptCount" | "chatCount";
  width: string;
  minWidth: number;
};

export const BACKLINK_OPPORTUNITY_COLUMNS: readonly BacklinkOpportunityColumn[] = [
  { id: "domain", width: "32%", minWidth: 200 },
  { id: "priority", width: "10%", minWidth: 96 },
  { id: "domainType", width: "14%", minWidth: 120 },
  { id: "platform", width: "12%", minWidth: 104 },
  { id: "promptCount", width: "16%", minWidth: 112 },
  { id: "chatCount", width: "16%", minWidth: 112 },
];

export const BACKLINK_OPPORTUNITY_MIN_WIDTH = BACKLINK_OPPORTUNITY_COLUMNS.reduce(
  (sum, column) => sum + column.minWidth,
  0,
);

export function backlinkOpportunityDomainCellStyle(): CSSProperties {
  const domain = BACKLINK_OPPORTUNITY_COLUMNS[0];
  return {
    minWidth: domain.minWidth,
    maxWidth: 0,
  };
}

export function backlinkOpportunityColumnColStyle(column: BacklinkOpportunityColumn): CSSProperties {
  return { width: column.width, minWidth: column.minWidth };
}

export type BacklinkOpportunityRow = {
  id: string;
  host: string;
  priority: OpportunityPriority;
  priorityLabel: string;
  domainType: string;
  platform: string;
  promptCount: number;
  chatCount: number;
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

const DOMAIN_TYPE_LABELS: Record<BacklinkOpportunityItem["domain_type"], string> = {
  enterprise: "企业/品牌官网",
  other: "其他",
};

export function buildBacklinkOpportunityRows(items: BacklinkOpportunityItem[]): BacklinkOpportunityRow[] {
  return items.map((item) => ({
    id: item.id,
    host: item.host,
    priority: item.priority,
    priorityLabel: PRIORITY_LABELS[item.priority],
    domainType: DOMAIN_TYPE_LABELS[item.domain_type],
    platform: item.platform,
    promptCount: item.prompt_count,
    chatCount: item.chat_count,
  }));
}

export type BacklinkOpportunitySortColumn = "priority" | "promptCount" | "chatCount";

export function sortBacklinkOpportunityRows(
  rows: BacklinkOpportunityRow[],
  column: BacklinkOpportunitySortColumn,
  dir: "asc" | "desc",
): BacklinkOpportunityRow[] {
  const sign = dir === "asc" ? 1 : -1;

  const valueOf = (row: BacklinkOpportunityRow): number => {
    if (column === "priority") return PRIORITY_ORDER[row.priority];
    if (column === "promptCount") return row.promptCount;
    return row.chatCount;
  };

  return [...rows].sort((a, b) => (valueOf(a) - valueOf(b)) * sign);
}

export function filterBacklinkOpportunityRows(
  rows: BacklinkOpportunityRow[],
  search: string,
): BacklinkOpportunityRow[] {
  const query = search.trim().toLowerCase();
  if (!query) return rows;
  return rows.filter((row) => row.host.toLowerCase().includes(query));
}
