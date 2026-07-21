import type { CSSProperties } from "react";

import type { BacklinkOpportunityDetailTab, BacklinkOpportunityItem, BacklinkOpportunitySortField, OpportunityPriority } from "@/types";

export type BacklinkOpportunityColumn = {
  id: "domain" | "domainType" | "priority" | "platform" | "citationCount" | "promptCount" | "chatCount";
  width: string;
  minWidth: number;
};

export const BACKLINK_OPPORTUNITY_COLUMNS: readonly BacklinkOpportunityColumn[] = [
  { id: "domain", width: "22%", minWidth: 180 },
  { id: "domainType", width: "12%", minWidth: 96 },
  { id: "priority", width: "10%", minWidth: 88 },
  { id: "platform", width: "16%", minWidth: 160 },
  { id: "citationCount", width: "13%", minWidth: 110 },
  { id: "promptCount", width: "13.5%", minWidth: 110 },
  { id: "chatCount", width: "13.5%", minWidth: 110 },
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
  domain: string;
  domainType: string;
  priority: OpportunityPriority;
  priorityLabel: string;
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

export function buildBacklinkOpportunityRows(items: BacklinkOpportunityItem[]): BacklinkOpportunityRow[] {
  return items.map((item) => ({
    id: item.id,
    domain: item.domain,
    domainType: item.domain_type ?? "",
    priority: item.priority,
    priorityLabel: PRIORITY_LABELS[item.priority],
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
