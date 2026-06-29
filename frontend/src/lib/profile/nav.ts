import { DASHBOARD_APP_BASE } from "@/lib/dashboard";
import type { ProfileTab } from "@/types";

export const PROFILE_TABS: { id: ProfileTab; label: string }[] = [
  { id: "account", label: "账户" },
  { id: "members", label: "成员" },
];

export const DEFAULT_PROFILE_TAB: ProfileTab = "account";

export const PROFILE_BASE_PATH = `${DASHBOARD_APP_BASE}/profile`;

export function parseProfileTab(value: string | null | undefined): ProfileTab {
  if (value && PROFILE_TABS.some((tab) => tab.id === value)) {
    return value as ProfileTab;
  }
  return DEFAULT_PROFILE_TAB;
}

export function profileTabPath(tab: ProfileTab = DEFAULT_PROFILE_TAB): string {
  return `${PROFILE_BASE_PATH}/${tab}`;
}

export function profileTabFromPathname(pathname: string): ProfileTab {
  const normalized = pathname.replace(/\/+$/, "");
  if (normalized === PROFILE_BASE_PATH) {
    return DEFAULT_PROFILE_TAB;
  }
  if (!normalized.startsWith(`${PROFILE_BASE_PATH}/`)) {
    return DEFAULT_PROFILE_TAB;
  }
  const rest = normalized.slice(`${PROFILE_BASE_PATH}/`.length);
  const segment = rest.split("/")[0] ?? "";
  return parseProfileTab(segment || null);
}
