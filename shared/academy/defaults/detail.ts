import { APP_LINK_KEYS } from "../../app-links";
import type { AcademySidebarCta } from "../types";

/** 详情侧栏 CTA（参考 academy-detail aside） */
export const academySidebarDefault: AcademySidebarCta = {
  eyebrow: "{{siteName}}",
  title: "检查 AI 是否正在推荐你的品牌",
  description: "生成免费的 GEO 诊断报告，查看品牌提及、引用、竞争差距和优化机会。",
  primaryLabel: "获取品牌 GEO 报告",
  primaryHref: APP_LINK_KEYS.register,
};

/** Hero CTA 下方备注 */
export const academyDetailHeroNotes = {
  note: "追踪 AI 搜索可见性",
} as const;
