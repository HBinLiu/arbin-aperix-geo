import { DASHBOARD_APP_BASE } from "@/lib/dashboard";
import type { BillingTab } from "@/types";

export const BILLING_TABS: { id: BillingTab; label: string }[] = [
  { id: "plan", label: "订阅计划" },
  { id: "details", label: "账单明细" },
];

export const DEFAULT_BILLING_TAB: BillingTab = "plan";

export const BILLING_BASE_PATH = `${DASHBOARD_APP_BASE}/billing`;

export function parseBillingTab(value: string | null | undefined): BillingTab {
  if (value && BILLING_TABS.some((tab) => tab.id === value)) {
    return value as BillingTab;
  }
  return DEFAULT_BILLING_TAB;
}

export function billingTabPath(tab: BillingTab = DEFAULT_BILLING_TAB): string {
  return `${BILLING_BASE_PATH}/${tab}`;
}

export function billingTabFromPathname(pathname: string): BillingTab {
  const normalized = pathname.replace(/\/+$/, "");
  if (normalized === BILLING_BASE_PATH) {
    return DEFAULT_BILLING_TAB;
  }
  if (!normalized.startsWith(`${BILLING_BASE_PATH}/`)) {
    return DEFAULT_BILLING_TAB;
  }
  const rest = normalized.slice(`${BILLING_BASE_PATH}/`.length);
  const segment = rest.split("/")[0] ?? "";
  return parseBillingTab(segment || null);
}
