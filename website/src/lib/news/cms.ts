import type { NewsListItem } from "@shared/news";
import type { CmsNewsDoc } from "@/lib/news/types";
import { resolveSiteCopyDeep } from "@/lib/site";

export function cmsDocToNewsListItem(doc: CmsNewsDoc): NewsListItem {
  return resolveSiteCopyDeep({
    slug: doc.slug,
    cardTitle: doc.cardTitle?.trim() || doc.slug,
    cardDescription: doc.cardDescription?.trim() || "",
    publishedAt: doc.publishedAt,
    sortOrder: doc.sortOrder ?? 0,
  });
}

/** CMS 列表；无数据时返回空数组 */
export function mergeNewsList(cms: CmsNewsDoc[] | null | undefined): NewsListItem[] {
  if (!cms?.length) return [];

  const merged = cms.map(cmsDocToNewsListItem);
  merged.sort((a, b) => {
    const orderDiff = (b.sortOrder ?? 0) - (a.sortOrder ?? 0);
    if (orderDiff !== 0) return orderDiff;
    const dateA = a.publishedAt ? Date.parse(a.publishedAt) : 0;
    const dateB = b.publishedAt ? Date.parse(b.publishedAt) : 0;
    return dateB - dateA;
  });

  return merged;
}

export function findNewsListItem(items: NewsListItem[], slug: string): NewsListItem | undefined {
  return items.find((item) => item.slug === slug);
}
