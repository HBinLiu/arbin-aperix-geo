import { DASHBOARD_APP_BASE } from "@/lib/dashboard";
import type { OpportunityTab } from "@/types";

export const OPPORTUNITY_TABS: { id: OpportunityTab; label: string }[] = [
  { id: "backlink", label: "引用信源" },
  { id: "competitor", label: "潜在竞品" },
  { id: "prompt", label: "潜在提示词" },
];

export const DEFAULT_OPPORTUNITY_TAB: OpportunityTab = "backlink";

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
  const rest = normalized.slice(`${OPPORTUNITY_BASE_PATH}/`.length);
  const segment = rest.split("/")[0] ?? "";
  return parseOpportunityTab(segment || null);
}

export const BACKLINK_OPPORTUNITY_DETAIL_PREFIX = `${OPPORTUNITY_BASE_PATH}/backlink/`;

export function backlinkOpportunityDetailPath(domain: string): string {
  return `${BACKLINK_OPPORTUNITY_DETAIL_PREFIX}${encodeURIComponent(domain)}`;
}

export function backlinkOpportunityDomainFromPathname(pathname: string): string | null {
  const normalized = pathname.replace(/\/+$/, "");
  if (!normalized.startsWith(BACKLINK_OPPORTUNITY_DETAIL_PREFIX)) {
    return null;
  }
  const encoded = normalized.slice(BACKLINK_OPPORTUNITY_DETAIL_PREFIX.length).split("/")[0] ?? "";
  if (!encoded) {
    return null;
  }
  try {
    return decodeURIComponent(encoded).trim().toLowerCase();
  } catch {
    return encoded.trim().toLowerCase();
  }
}