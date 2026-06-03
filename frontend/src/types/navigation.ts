import type { LucideIcon } from "lucide-react";

export type DashboardNavId =
  | "overview"
  | "analysis"
  | "rank"
  | "opportunities"
  | "agent"
  | "brand";

export type DashboardNavItem = {
  id: DashboardNavId;
  label: string;
  icon: LucideIcon;
  badge?: string;
};

export type DashboardNavSection = {
  title: string;
  items: DashboardNavItem[];
};

export type AnalysisDimension = "visibility" | "prompt" | "platform" | "sentiment" | "citation";
