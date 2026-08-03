import { APP_LINK_KEYS } from "../../app-links";
import type { BlogSidebarCta } from "../types";

/** 详情侧栏「体验」卡（参考 blog-detail aside） */
export const blogSidebarDefault: BlogSidebarCta = {
  title: "体验 {{siteName}}",
  items: [
    "在 AI 搜索引擎中追踪您的品牌可见性",
    "了解您的内容是如何被 AI 排名、引用或忽略的",
    "识别可见性差距和内容机会",
    "通过竞争机会创建与优化内容，获取反向链接",
  ],
  description:
    "即时了解 AI 搜索引擎如何解析、排名和引用您的内容 —— 并针对真正影响 AI 回答的因素进行优化。",
  primaryLabel: "开始注册试用",
  primaryHref: APP_LINK_KEYS.register,
  note: "",
};

/** Hero CTA 下方备注（参考：追踪可见性 · 无需安装） */
export const blogDetailHeroNotes = {
  note: "追踪 AI 搜索可见性",
} as const;
