/** 博客分类（列表筛选胶囊） */
export type BlogCategory = {
  slug: string;
  label: string;
  sortOrder?: number;
};

/** 作者摘要（卡片 / Hero 元信息） */
export type BlogAuthorSummary = {
  slug: string;
  name: string;
  avatarUrl?: string;
};

/** 博客列表/卡片项 */
export type BlogListItem = {
  slug: string;
  cardTitle: string;
  cardDescription: string;
  coverUrl?: string;
  categorySlug?: string;
  categoryLabel?: string;
  author?: BlogAuthorSummary;
  publishedAt?: string;
  updatedAt?: string;
  readMinutes?: number;
  sortOrder?: number;
  isFeatured?: boolean;
  isEditorsPick?: boolean;
  editorsPickOrder?: number;
};

/** 详情页 Hero */
export type BlogHeroDetail = {
  title: string;
  lead: string;
  coverUrl?: string;
  categoryLabel?: string;
  author?: BlogAuthorSummary;
  publishedLabel: string;
  updatedLabel: string;
  readMinutes: number;
  readTimeLabel: string;
  primaryHref: string;
  primaryLabel: string;
};

export type BlogTocItem = {
  id: string;
  label: string;
};

/** 详情右侧 sticky「体验」卡（在目录上方） */
export type BlogSidebarCta = {
  title: string;
  items: string[];
  /** 卡内灰色说明文案 */
  description?: string;
  primaryLabel: string;
  primaryHref: string;
  note?: string;
};
