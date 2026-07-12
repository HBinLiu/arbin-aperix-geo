import type { CtaContent } from "@/lib/home";
import type { PageSeo } from "@/lib/seo";
import type { TeamSolutionSlug } from "@shared/faq/pages";

export type SolutionWhyCard = {
  number: string;
  title: string;
  bodyHtml: string;
};

export type SolutionChallengeIcon = "coins" | "git-branch" | "trending-down" | "user-x";

export type SolutionChallengeCard = {
  title: string;
  description: string;
  icon: SolutionChallengeIcon;
};

export type SolutionPillarIcon =
  | "layout-dashboard"
  | "users"
  | "shield"
  | "files"
  | "code";

export type SolutionPillar = {
  title: string;
  description: string;
  icon: SolutionPillarIcon;
};

export type SolutionFeatureCard = {
  title: string;
  description: string;
  image: string;
  area: "card1" | "card2" | "card3" | "card4" | "card5";
};

export type SolutionWorkflowStep = {
  text: string;
  highlight?: boolean;
};

export type SolutionWorkflow = {
  title: string;
  accent: "primary" | "orange";
  steps: SolutionWorkflowStep[];
};

export type TeamSolutionContent = {
  slug: TeamSolutionSlug;
  seo: PageSeo;
  badge: string;
  hero: {
    title: string;
    description: string;
    ctaLabel: string;
    ctaHref: string;
  };
  why: {
    title: string;
    cards: SolutionWhyCard[];
  };
  challenges: {
    title: string;
    cards: SolutionChallengeCard[];
  };
  solution: {
    title: string;
    description: string;
    pillars: SolutionPillar[];
  };
  features: {
    title: string;
    cards: SolutionFeatureCard[];
  };
  workflows: {
    title: string;
    items: SolutionWorkflow[];
  };
  cta: CtaContent;
};
