import type { CSSProperties } from "react";

import type { BacklinkOpportunityDetailTab, BacklinkOpportunityItem, BacklinkOpportunitySortField, OpportunityPriority } from "@/types";

export type BacklinkOpportunityColumn = {
  id: "domain" | "priority" | "domainType" | "platform" | "citationCount" | "promptCount" | "chatCount";
  width: string;
  minWidth: number;
};

export const BACKLINK_OPPORTUNITY_COLUMNS: readonly BacklinkOpportunityColumn[] = [
  { id: "domain", width: "25%", minWidth: 200 },
  { id: "priority", width: "12%", minWidth: 100 },
  { id: "domainType", width: "13%", minWidth: 120 },
  { id: "platform", width: "14%", minWidth: 180 },
  { id: "citationCount", width: "12%", minWidth: 120 },
  { id: "promptCount", width: "12%", minWidth: 120 },
  { id: "chatCount", width: "12%", minWidth: 120 },
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
  platforms: string[];
  citationCount: number;
  promptCount: number;
  chatCount: number;
};

const PRIORITY_LABELS: Record<OpportunityPriority, string> = {
  high: "高",
  medium: "中",
  low: "低",
};

export function backlinkPriorityLabel(priority: OpportunityPriority): string {
  return PRIORITY_LABELS[priority];
}

export const BACKLINK_OPPORTUNITY_DETAIL_TABS: { id: BacklinkOpportunityDetailTab; label: string }[] = [
  { id: "pages", label: "引用率" },
  { id: "prompt", label: "提示词" },
];

const DOMAIN_TYPE_FALLBACK = "其它类型";

export function buildBacklinkOpportunityRows(items: BacklinkOpportunityItem[]): BacklinkOpportunityRow[] {
  return items.map((item) => ({
    id: item.id,
    host: item.host,
    priority: item.priority,
    priorityLabel: PRIORITY_LABELS[item.priority],
    domainType: item.domain_type?.trim() || DOMAIN_TYPE_FALLBACK,
    platforms: item.platforms,
    citationCount: item.citation_count,
    promptCount: item.prompt_count,
    chatCount: item.chat_count,
  }));
}

export type BacklinkOpportunitySortColumn =
  | "priority"
  | "citationCount"
  | "promptCount"
  | "chatCount";

export function backlinkOpportunitySortToApiField(
  column: BacklinkOpportunitySortColumn,
  dir: "asc" | "desc",
): { sortBy: BacklinkOpportunitySortField; order: "asc" | "desc" } {
  const sortBy: BacklinkOpportunitySortField =
    column === "citationCount"
      ? "citation_count"
      : column === "promptCount"
        ? "prompt_count"
        : column === "chatCount"
          ? "chat_count"
          : "priority";
  return { sortBy, order: dir };
}
