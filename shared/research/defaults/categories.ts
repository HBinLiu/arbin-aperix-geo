import type { ResearchCategory } from "../types";

/** CMS 不可用时的分类回退（与 seed 对齐） */
export const researchCategoryDefaults: ResearchCategory[] = [
  {
    slug: "industry",
    label: "行业报告",
    sortOrder: 1,
  },
];
