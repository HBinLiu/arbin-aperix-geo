import type { CtaContent } from "@/lib/home";
import type { PageSeo } from "@/lib/seo";
import type { SceneSlug } from "@shared/faq/pages";

export type SceneWhyIcon =
  | "activity"
  | "ai-orbit"
  | "bar-chart"
  | "brain"
  | "clock"
  | "help-circle"
  | "layers"
  | "lightbulb"
  | "quote"
  | "search"
  | "shield"
  | "target"
  | "timeline"
  | "zap";

export type SceneMetricIcon =
  | "activity"
  | "chart-no-axes-column"
  | "chart-pie"
  | "clock"
  | "layers"
  | "rocket"
  | "search"
  | "sentiment"
  | "shield"
  | "target"
  | "trending-up"
  | "users";

export type SceneWorkflowIcon =
  | "briefcase"
  | "chart-rising"
  | "network-nodes"
  | "quote"
  | "shield"
  | "target";

export type SceneDiagnosticGapIcon = "eye-off" | "git-branch" | "hourglass" | "pie-chart";

export const SCENE_DIAGNOSTIC_GAP_ICONS: SceneDiagnosticGapIcon[] = [
  "eye-off",
  "git-branch",
  "pie-chart",
  "hourglass",
];

export type SceneDiagnosticGap = {
  code: string;
  label: string;
  description: string;
  icon?: SceneDiagnosticGapIcon;
};

export type SceneWhyCard = {
  icon: SceneWhyIcon;
  text: string;
};

export type ScenePillar = {
  title: string;
  description: string;
  image: string;
};

export type SceneWorkflow = {
  title: string;
  icon: SceneWorkflowIcon;
  challenge: string;
  action: string;
  result: string;
};

export type SceneMetric = {
  icon: SceneMetricIcon;
  title: string;
  description: string;
};

export type SceneChecklistItem = {
  number: string;
  title: string;
  description: string;
  accent: "primary" | "muted";
};

export type SceneContent = {
  slug: SceneSlug;
  seo: PageSeo;
  badge: string;
  hero: {
    title: string;
    description: string;
    ctaLabel: string;
    ctaHref: string;
  };
  diagnostic: {
    title: string;
    userQuestion: string;
    summary: string;
    gaps: SceneDiagnosticGap[];
  };
  why: {
    title: string;
    cards: SceneWhyCard[];
  };
  solution: {
    title: string;
    pillars: ScenePillar[];
  };
  workflows: {
    title: string;
    items: SceneWorkflow[];
  };
  metrics: {
    title: string;
    cards: SceneMetric[];
  };
  checklist: {
    title: string;
    items: SceneChecklistItem[];
  };
  cta: CtaContent;
};
