import { researchCategoryDefaults, type ResearchCategory, type ResearchListItem } from "@shared/research";
import type { CmsResearchCategoryDoc, CmsResearchDoc } from "@/lib/research/types";
import { resolveResearchCategorySlug } from "@/lib/research/types";
import { resolveResearchMediaUrl } from "@/lib/research/media";
import { resolveSiteCopyDeep } from "@/lib/site";

export function cmsDocToResearchListItem(doc: CmsResearchDoc): ResearchListItem {
  return resolveSiteCopyDeep({
    slug: doc.slug,
    categorySlug: resolveResearchCategorySlug(doc.category, "industry"),
    cardTitle: doc.cardTitle?.trim() || doc.slug,
    cardDescription: doc.cardDescription?.trim() || "",
    coverSrc: resolveResearchMediaUrl(doc.cover),
    publishedAt: doc.publishedAt ?? undefined,
    sortOrder: doc.sortOrder ?? 0,
  });
}

function sortCategories(categories: ResearchCategory[]): ResearchCategory[] {
  return [...categories].sort((a, b) => {
    const orderDiff = (b.sortOrder ?? 0) - (a.sortOrder ?? 0);
    if (orderDiff !== 0) return orderDiff;
    return a.label.localeCompare(b.label, "zh-CN");
  });
}

/** CMS 分类优先；空则回退 shared defaults */
export function mergeResearchCategories(
  cms: CmsResearchCategoryDoc[] | null | undefined,
): ResearchCategory[] {
  const defaults = resolveSiteCopyDeep(researchCategoryDefaults);
  if (!cms?.length) return sortCategories(defaults);

  const merged = cms.map((doc) =>
    resolveSiteCopyDeep({
      slug: doc.slug,
      label: doc.label?.trim() || doc.slug,
      sortOrder: doc.sortOrder ?? 0,
    }),
  );

  return sortCategories(merged);
}

/** CMS 列表优先；无 CMS 数据时返回空数组 */
export function mergeResearchList(cms: CmsResearchDoc[] | null | undefined): ResearchListItem[] {
  if (!cms?.length) return [];

  const merged = cms.map(cmsDocToResearchListItem);
  merged.sort((a, b) => {
    const orderDiff = (b.sortOrder ?? 0) - (a.sortOrder ?? 0);
    if (orderDiff !== 0) return orderDiff;
    const dateA = a.publishedAt ? Date.parse(a.publishedAt) : 0;
    const dateB = b.publishedAt ? Date.parse(b.publishedAt) : 0;
    return dateB - dateA;
  });

  return merged;
}

export function findResearchListItem(
  items: ResearchListItem[],
  slug: string,
): ResearchListItem | undefined {
  return items.find((item) => item.slug === slug);
}
