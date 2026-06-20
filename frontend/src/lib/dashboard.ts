import {
  BarChart3,
  Bot,
  LayoutGrid,
  Lightbulb,
  MessageSquare,
  Stethoscope,
  Tag,
  Trophy,
} from "lucide-react";
import type { DashboardNavId, DashboardNavItem, DashboardNavSection } from "@/types";

export const DASHBOARD_NAV_SECTIONS: DashboardNavSection[] = [
  {
    title: "常规",
    items: [{ id: "overview", label: "概述", icon: LayoutGrid }],
  },
  {
    title: "洞察",
    items: [
      { id: "analysis", label: "分析", icon: BarChart3 },
      { id: "rank", label: "排行榜", icon: Trophy },
      { id: "opportunity", label: "潜在机会", icon: Lightbulb },
    ],
  },
  {
    title: "操作",
    items: [
      { id: "agent", label: "智能体", icon: Bot },
      { id: "diagnosis", label: "诊断中心", icon: Stethoscope },
    ],
  },
  {
    title: "配置",
    items: [
      { id: "brand", label: "品牌", icon: Tag },
      { id: "prompt", label: "提示词", icon: MessageSquare },
    ],
  },
];

export const DEFAULT_DASHBOARD_NAV_ID: DashboardNavId = "overview";

export const DASHBOARD_APP_BASE = "/app";

export const DASHBOARD_SETUP_PATH = `${DASHBOARD_APP_BASE}/setup`;

/** 各菜单项对应的路由 path segment（不含 /app 前缀）；overview 使用 index 路由。 */
export const DASHBOARD_NAV_SEGMENT: Record<Exclude<DashboardNavId, "overview">, string> = {
  analysis: "analysis",
  rank: "rank",
  opportunity: "opportunity",
  agent: "agent",
  diagnosis: "diagnosis",
  prompt: "prompt",
  brand: "brand",
};

const SEGMENT_TO_NAV_ID = new Map<string, DashboardNavId>(
  Object.entries(DASHBOARD_NAV_SEGMENT).map(([id, segment]) => [segment, id as DashboardNavId]),
);

export function dashboardNavToPath(id: DashboardNavId): string {
  if (id === "overview") {
    return DASHBOARD_APP_BASE;
  }
  if (id === "analysis") {
    return `${DASHBOARD_APP_BASE}/analysis/visibility`;
  }
  if (id === "opportunity") {
    return `${DASHBOARD_APP_BASE}/opportunity/content`;
  }
  return `${DASHBOARD_APP_BASE}/${DASHBOARD_NAV_SEGMENT[id]}`;
}

export function dashboardNavIdFromPath(pathname: string): DashboardNavId {
  const normalized = pathname.replace(/\/+$/, "");
  if (normalized === DASHBOARD_APP_BASE) {
    return DEFAULT_DASHBOARD_NAV_ID;
  }
  if (!normalized.startsWith(`${DASHBOARD_APP_BASE}/`)) {
    return DEFAULT_DASHBOARD_NAV_ID;
  }
  const segment = normalized.slice(`${DASHBOARD_APP_BASE}/`.length).split("/")[0] ?? "";
  return SEGMENT_TO_NAV_ID.get(segment) ?? DEFAULT_DASHBOARD_NAV_ID;
}

const NAV_BY_ID = new Map<DashboardNavId, DashboardNavItem>(
  DASHBOARD_NAV_SECTIONS.flatMap((section) => section.items).map((item) => [item.id, item]),
);

export function getDashboardNavItem(id: DashboardNavId): DashboardNavItem {
  const item = NAV_BY_ID.get(id);
  if (!item) {
    return NAV_BY_ID.get(DEFAULT_DASHBOARD_NAV_ID)!;
  }
  return item;
}
