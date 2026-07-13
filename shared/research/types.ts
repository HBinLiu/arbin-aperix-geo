/** 研究报告列表分类（CMS `research-categories`） */
export type ResearchCategory = {
  slug: string;
  label: string;
  sortOrder?: number;
};

/** 列表卡片上的分类 slug（用于 ?category= 筛选） */
export type ResearchCategorySlug = string;

/** 列表页卡片（Payload researches 列表字段） */
export type ResearchListItem = {
  slug: string;
  categorySlug: ResearchCategorySlug;
  cardTitle: string;
  cardDescription: string;
  coverSrc: string;
  publishedAt?: string;
  sortOrder?: number;
};

/** 详情页 Hero（固定模板，代码 defaults 维护） */
export type ResearchHeroLink = {
  label: string;
  href: string;
  external?: boolean;
};

export type ResearchHeroDetail = {
  badge: string;
  title: string;
  subtitle: string;
  /** 详情页标题下方标签（纯展示，来自 CMS cardLabels） */
  labels: string[];
  actions: ResearchHeroLink[];
  proof: string[];
};

/** 从正文 H2 自动提取；label 为分隔符前的短标题 */
export type ResearchTocItem = {
  id: string;
  number: string;
  label: string;
};

/** 详情页右侧固定 CTA（组件内写死文案结构，此处仅类型参考） */
export type ResearchSidebarCta = {
  kicker: string;
  title: string;
  description: string;
  bullets: string[];
  primaryLabel: string;
  primaryHref: string;
  secondaryLabel: string;
  secondaryHref: string;
  footnote: string;
};
