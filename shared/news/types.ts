/** 新闻列表项（Payload `news` 列表字段） */
export type NewsListItem = {
  slug: string;
  cardTitle: string;
  cardDescription: string;
  publishedAt?: string;
  sortOrder?: number;
};

/** 按月分组（列表页卡片） */
export type NewsMonthGroup = {
  key: string;
  label: string;
  items: NewsListItem[];
};

/** 详情页 Hero */
export type NewsHeroDetail = {
  tag: string;
  title: string;
  lead: string;
  sourceAuthor: string;
  sourceUrl: string;
  sourceLabel: string;
  publishedLabel: string;
  readMinutes: number;
  readTimeLabel: string;
  editorNote: string;
  primaryHref: string;
  primaryLabel: string;
};

/** 从正文 H2 自动提取；label 为分隔符前的短标题 */
export type NewsTocItem = {
  id: string;
  label: string;
};

/** 详情页右侧固定 CTA */
export type NewsSidebarCta = {
  eyebrow: string;
  title: string;
  description: string;
  primaryLabel: string;
  primaryHref: string;
};
