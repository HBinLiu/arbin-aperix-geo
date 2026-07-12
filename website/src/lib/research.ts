import type { ResearchCategory, ResearchListItem } from "@shared/research";

export type { ResearchCategory, ResearchCategorySlug, ResearchListItem, ResearchTocItem } from "@shared/research";
export { RESEARCH_BLOCK_SLUGS } from "@shared/research/blocks";

export const researchHero = {
  title: "基于真实数据的 AI 搜索与 SEO 研究",
  description: "研究报告、基准测试和咨询洞察，帮助品牌在 AI 驱动和传统搜索中赢得可见性。",
  ctaLabel: "开始试用",
  ctaHref: "/auth/register",
};

export const researchReportsSection = {
  title: "行业研究报告",
  subtitle: "为 SEO 和 AI 社区提供深度分析和数据驱动的洞察",
};

export function buildResearchCategoryOptions(
  categories: ResearchCategory[],
): Array<{ id: string; label: string }> {
  return [
    { id: "all", label: "所有分类" },
    ...categories.map((category) => ({
      id: category.slug,
      label: category.label,
    })),
  ];
}

/** @deprecated CMS 无数据时列表为空 */
export const researchReportDefaults: ResearchListItem[] = [];

export function researchHref(slug: string): string {
  return `/research/${slug}/`;
}

export function findResearchReport(slug: string, reports: ResearchListItem[]): ResearchListItem | undefined {
  return reports.find((report) => report.slug === slug);
}

/** 列表页分页 */
export {
  RESEARCH_LIST_PAGE_SIZE,
  buildResearchListUrl,
  getResearchPageItems,
  parseResearchListCategory,
  parseResearchListPage,
  readResearchListCategory,
} from "@/lib/research/pagination";

export function paginateResearchReports(
  reports: ResearchListItem[],
  page: number,
  pageSize: number,
): { items: ResearchListItem[]; total: number; totalPages: number; page: number } {
  const total = reports.length;
  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  const safePage = Math.min(Math.max(1, page), totalPages);
  const start = (safePage - 1) * pageSize;
  return {
    items: reports.slice(start, start + pageSize),
    total,
    totalPages,
    page: safePage,
  };
}
