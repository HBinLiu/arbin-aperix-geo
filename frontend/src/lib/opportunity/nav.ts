import { DASHBOARD_APP_BASE } from "@/lib/dashboard";
import type { OpportunityTab } from "@/types";

export const OPPORTUNITY_TABS: { id: OpportunityTab; label: string }[] = [
  { id: "content", label: "内容" },
  { id: "backlink", label: "反向链接" },
  { id: "social", label: "社交媒体" },
];

export const DEFAULT_OPPORTUNITY_TAB: OpportunityTab = "content";

export const OPPORTUNITY_BASE_PATH = `${DASHBOARD_APP_BASE}/opportunity`;

export function parseOpportunityTab(value: string | null | undefined): OpportunityTab {
  if (value && OPPORTUNITY_TABS.some((tab) => tab.id === value)) {
    return value as OpportunityTab;
  }
  return DEFAULT_OPPORTUNITY_TAB;
}

export function opportunityTabPath(tab: OpportunityTab = DEFAULT_OPPORTUNITY_TAB): string {
  return `${OPPORTUNITY_BASE_PATH}/${tab}`;
}

export function opportunityTabFromPathname(pathname: string): OpportunityTab {
  const normalized = pathname.replace(/\/+$/, "");
  if (normalized === OPPORTUNITY_BASE_PATH) {
    return DEFAULT_OPPORTUNITY_TAB;
  }
  if (!normalized.startsWith(`${OPPORTUNITY_BASE_PATH}/`)) {
    return DEFAULT_OPPORTUNITY_TAB;
  }
  const segment = normalized.slice(`${OPPORTUNITY_BASE_PATH}/`.length).split("/")[0] ?? "";
  return parseOpportunityTab(segment || null);
}
