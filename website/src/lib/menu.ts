import type { ComponentType } from "react";

import AnswerPreview from "@/components/menu/previews/AnswerPreview";
import ContentCreationPreview from "@/components/menu/previews/ContentCreationPreview";
import FindTopicsPreview from "@/components/menu/previews/FindTopicsPreview";
import PromptPreview from "@/components/menu/previews/PromptPreview";
import type { PlatformId } from "@shared/platform";
import { HERO_PLATFORM_IDS, platformLabel, platformLogoPublicPath } from "@shared/platform";
import { monitorHref } from "@/lib/platform/monitor";

export type MenuPreviewId =
  | "answer-engine"
  | "prompt"
  | "find-topics"
  | "content-creation";

export type MenuPreviewProps = {
  className?: string;
};

export const MENU_PREVIEWS: Record<MenuPreviewId, ComponentType<MenuPreviewProps>> = {
  "answer-engine": AnswerPreview,
  prompt: PromptPreview,
  "find-topics": FindTopicsPreview,
  "content-creation": ContentCreationPreview,
};

export type PlatformMenuItem = {
  title: string;
  description: string;
  href: string;
  preview: MenuPreviewId;
};

export type PlatformMenuSection = {
  title: string;
  items: PlatformMenuItem[];
};

export type PlatformNavLink = {
  label: string;
  href: string;
};

export const platformMenuIntro = {
  title: "平台",
  subtitle: "在线可见性，化繁为简。",
};

/** Mega Menu 顶部展示的 AI 平台（含「更多」占位） */
export const platformMenuPlatforms: Array<
  | { type: "platform"; id: PlatformId }
  | { type: "more"; label: string; href: string }
> = [
  ...HERO_PLATFORM_IDS.map((id) => ({ type: "platform" as const, id })),
  { type: "more", label: "更多", href: "#faq" },
];

export function platformMenuPlatformLabel(
  entry: (typeof platformMenuPlatforms)[number],
): string {
  if (entry.type === "more") return entry.label;
  return platformLabel(entry.id);
}

export function platformMenuPlatformLogo(
  entry: (typeof platformMenuPlatforms)[number],
): string | null {
  if (entry.type === "more") return null;
  return platformLogoPublicPath(entry.id);
}

export function platformMenuPlatformHref(
  entry: (typeof platformMenuPlatforms)[number],
): string {
  if (entry.type === "more") return entry.href;
  return monitorHref(entry.id);
}

export const platformMenuSections: PlatformMenuSection[] = [
  {
    title: "提升 AI 平台可见性",
    items: [
      {
        title: "回答引擎洞察",
        description: "查看 AI 如何介绍您的品牌",
        href: "/platform/answer-engine-insights",
        preview: "answer-engine",
      },
      {
        title: "提示词探索",
        description: "发现高价值查询，查询扇出洞察",
        href: "/platform/prompt-volumes-explorer",
        preview: "prompt",
      },
      {
        title: "发现机会与差距",
        description: "GEO 内容与来源覆盖缺口分析",
        href: "/platform/find-topics-ideas",
        preview: "find-topics",
      },
      {
        title: "内容创作与优化",
        description: "AI 辅助内容创作与优化",
        href: "/app",
        preview: "content-creation",
      },
    ],
  },
];

export const defaultHeaderLinks: PlatformNavLink[] = [
  { label: "定价", href: "#cta" },
  { label: "关于我们", href: "#faq" },
];

export type ResourcesMenuItem = {
  title: string;
  description: string;
  href: string;
};

export type ResourcesMenuSection = {
  title: string;
  items: ResourcesMenuItem[];
};

export const resourcesMenuIntro = {
  title: "资源",
  subtitle: "学习、探索与放大影响力。",
};

export const resourcesMenuSections: ResourcesMenuSection[] = [
  {
    title: "探索",
    items: [
      {
        title: "研究",
        description: "数据报告与行业趋势",
        href: "#faq",
      },
      {
        title: "新闻",
        description: "每周 AI 与产品新闻资讯",
        href: "#faq",
      },
      {
        title: "更新日志",
        description: "产品功能更新与改进日志",
        href: "#faq",
      },
    ],
  },
  {
    title: "学习",
    items: [
      {
        title: "学院",
        description: "GEO 与 SEO 指南",
        href: "#faq",
      },
      {
        title: "博客",
        description: "由经验驱动的 AI 可见性实践",
        href: "#faq",
      },
      {
        title: "文档指南",
        description: "产品文档与实施指南",
        href: "#faq",
      },
    ],
  },
  {
    title: "免费工具",
    items: [
      {
        title: "浏览器扩展",
        description: "Aperix 人工智能搜索分析器",
        href: "/app",
      },
      {
        title: "免费 SEO 与 GEO 报告",
        description: "获取您的 AI 品牌审计",
        href: "/app",
      },
      {
        title: "LLMs.txt 生成器",
        description: "生成一份面向 AI 的 llms.txt 文件",
        href: "/app",
      },
      {
        title: "单页审计",
        description: "快速审计单个页面是否适合被 AI 理解和引用",
        href: "/app",
      },
      {
        title: "热门提示词发现器",
        description: "发现用户在 AI 引擎中搜索的热门提示词",
        href: "/app",
      },
      {
        title: "AI 文章生成器",
        description: "使用 AI 生成高质量文章",
        href: "/app",
      },
      {
        title: "AI 抓取检查器",
        description: "检查你的网站内容是否做好了 AI 就绪准备",
        href: "/app",
      },
    ],
  },
];
