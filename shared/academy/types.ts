/** 学院分类（列表筛选胶囊） */
export type AcademyCategory = {
  slug: string;
  label: string;
  sortOrder?: number;
};

/** 学院列表/卡片项 */
export type AcademyListItem = {
  slug: string;
  cardTitle: string;
  cardDescription: string;
  coverUrl?: string;
  categorySlug?: string;
  categoryLabel?: string;
  tag?: string;
  publishedAt?: string;
  updatedAt?: string;
  readMinutes?: number;
  sortOrder?: number;
  isFeatured?: boolean;
  isEditorsPick?: boolean;
  editorsPickOrder?: number;
};

/** 详情页 Hero（居中布局，对齐学院参考稿） */
export type AcademyHeroDetail = {
  tag: string;
  title: string;
  lead: string;
  coverUrl?: string;
  categoryLabel?: string;
  publishedLabel: string;
  updatedLabel: string;
  readMinutes: number;
  readTimeLabel: string;
  primaryHref: string;
  primaryLabel: string;
};

export type AcademyTocItem = {
  id: string;
  label: string;
};

/** 详情右侧 sticky CTA（目录上方；对齐新闻侧栏结构） */
export type AcademySidebarCta = {
  eyebrow: string;
  title: string;
  description: string;
  primaryLabel: string;
  primaryHref: string;
};
