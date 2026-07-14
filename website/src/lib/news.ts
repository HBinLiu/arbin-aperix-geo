import type { NewsListItem } from "@shared/news";
import { appLinks } from "@/lib/app-links";

export type { NewsHeroDetail, NewsListItem, NewsMonthGroup, NewsSidebarCta, NewsTocItem } from "@shared/news";
export { newsSidebarDefault } from "@shared/news";

export const newsHero = {
  title: "每周 AI 与产品新闻",
  description: "聚合每周 AI 产品动态、模型发布、生态变化与关键行业消息。",
  ctaLabel: "开始试用",
  ctaHref: appLinks.register,
};

export const newsListSection = {
  title: "新闻 archive",
  subtitle: "按月份浏览最新 AI 与 GEO 相关动态。",
};

export function newsHref(slug: string): string {
  return `/news/${slug}/`;
}

export function findNewsItem(slug: string, items: NewsListItem[]): NewsListItem | undefined {
  return items.find((item) => item.slug === slug);
}

export { cmsDocToNewsListItem, findNewsListItem, mergeNewsList } from "@/lib/news/cms";
export { buildNewsDetail, type NewsDetailViewModel } from "@/lib/news/detail";
export { newsRichTextToHtml, newsHtmlConverters } from "@/lib/news/body";
export { extractNewsToc, slugifyHeading } from "@/lib/news/toc";
export { NEWS_BLOCK_SLUGS } from "@shared/news/blocks";
export { groupNewsByMonth, NEWS_LIST_INITIAL_VISIBLE } from "@/lib/news/group";
