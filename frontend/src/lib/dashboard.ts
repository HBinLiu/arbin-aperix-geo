import {
  BarChart3,
  BookOpen,
  LayoutGrid,
  Lightbulb,
  MessageSquare,
  Settings,
  Stethoscope,
  Tag,
  Trophy,
  Wallet,
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
      { id: "diagnosis", label: "诊断中心", icon: Stethoscope },
      { id: "opportunity", label: "潜在机会", icon: Lightbulb },
    ],
  },
  {
    title: "运营",
    items: [
      { id: "knowledge", label: "知识库", icon: BookOpen },
      //{ id: "agent", label: "媒体发稿", icon: Bot },
    ],
  },
  {
    title: "配置",
    items: [
      { id: "brand", label: "品牌", icon: Tag },
      { id: "prompt", label: "提示词", icon: MessageSquare },
    ],
  },
  {
    title: "账户",
    items: [
      { id: "profile", label: "账户设置", icon: Settings },
      { id: "billing", label: "订阅与账单", icon: Wallet },
    ],
  },
];

export const DEFAULT_DASHBOARD_NAV_ID: DashboardNavId = "overview";

/** 控制台挂在站点根（app.aperix.cn/）；空字符串，子路径用 dashboardPath 拼接。 */
export const DASHBOARD_APP_BASE = "";

/** 拼控制台绝对路径：dashboardPath("billing", "plan") → "/billing/plan" */
export function dashboardPath(...segments: string[]): string {
  const parts = segments.map((s) => s.replace(/^\/+|\/+$/g, "")).filter(Boolean);
  return parts.length === 0 ? "/" : `/${parts.join("/")}`;
}

export const DASHBOARD_SETUP_PATH = dashboardPath("setup");

/** 各菜单项对应的路由 path segment（不含站点根）；overview 使用 index 路由。 */
export const DASHBOARD_NAV_SEGMENT: Record<Exclude<DashboardNavId, "overview">, string> = {
  analysis: "analysis",
  rank: "rank",
  opportunity: "opportunity",
  knowledge: "knowledge",
  agent: "agent",
  diagnosis: "diagnosis",
  prompt: "prompt",
  brand: "brand",
  profile: "profile",
  billing: "billing",
};

const SEGMENT_TO_NAV_ID = new Map<string, DashboardNavId>(
  Object.entries(DASHBOARD_NAV_SEGMENT).map(([id, segment]) => [segment, id as DashboardNavId]),
);

export function dashboardNavToPath(id: DashboardNavId): string {
  if (id === "overview") {
    return "/";
  }
  if (id === "analysis") {
    return dashboardPath("analysis", "visibility");
  }
  if (id === "opportunity") {
    return dashboardPath("opportunity", "backlink");
  }
  if (id === "billing") {
    return dashboardPath("billing", "plan");
  }
  if (id === "profile") {
    return dashboardPath("profile", "account");
  }
  return dashboardPath(DASHBOARD_NAV_SEGMENT[id]);
}

export function dashboardNavIdFromPath(pathname: string): DashboardNavId {
  const normalized = pathname.replace(/\/+$/, "") || "/";
  if (normalized === "/") {
    return DEFAULT_DASHBOARD_NAV_ID;
  }
  const segment = normalized.replace(/^\//, "").split("/")[0] ?? "";
  if (segment === "auth" || segment === "app") {
    return DEFAULT_DASHBOARD_NAV_ID;
  }
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
