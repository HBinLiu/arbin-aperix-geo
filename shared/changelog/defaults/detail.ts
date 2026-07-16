import type { ChangelogSidebarCta } from "../types";

/** 详情侧栏 CTA（CMS 不配置） */
export const changelogSidebarDefault: ChangelogSidebarCta = {
  title: "体验 {{siteName}}",
  items: [
    "监测品牌在 AI 回答中的可见度",
    "发现高价值提示词与内容机会",
    "用数据驱动 GEO 内容策略",
  ],
  description: "立即开始试用，探索 {{siteName}} 的 GEO 监测与内容能力。",
  primaryLabel: "立即开始试用",
  primaryHref: "register",
};

export const changelogListHero = {
  eyebrow: "产品更新",
  title: "更新日志",
  description: "集中查看 {{siteName}} 的产品发布、界面优化与问题修复。",
} as const;
