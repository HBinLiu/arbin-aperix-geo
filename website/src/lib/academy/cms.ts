import type { AcademyCategory, AcademyListItem } from "@shared/academy";
import type { CmsAcademyCategoryDoc, CmsAcademyCategoryRef, CmsAcademyDoc } from "@/lib/academy/types";
import { resolveAcademyMediaUrl } from "@/lib/academy/media";
import { resolveSiteCopyDeep } from "@/lib/site";

function resolveCategory(
  category: CmsAcademyCategoryRef | undefined,
): { slug?: string; label?: string } {
  if (!category || typeof category === "number" || typeof category === "string") {
    return {};
  }
  const slug = category.slug?.trim();
  const label = category.label?.trim();
  return {
    slug: slug || undefined,
    label: label || slug || undefined,
  };
}

export function cmsDocToAcademyListItem(doc: CmsAcademyDoc): AcademyListItem {
  const category = resolveCategory(doc.category);
  const tag = doc.tag?.trim() || category.label || undefined;
  return resolveSiteCopyDeep({
    slug: doc.slug,
    cardTitle: doc.cardTitle?.trim() || doc.slug,
    cardDescription: doc.cardDescription?.trim() || "",
    coverUrl: resolveAcademyMediaUrl(doc.cover ?? null) || undefined,
    categorySlug: category.slug,
    categoryLabel: category.label,
    tag,
    publishedAt: doc.publishedAt,
    updatedAt: doc.updatedAt ?? doc.publishedAt,
    readMinutes: doc.readMinutes ?? 5,
    sortOrder: doc.sortOrder ?? 0,
    isFeatured: Boolean(doc.isFeatured),
    isEditorsPick: Boolean(doc.isEditorsPick),
    editorsPickOrder: doc.editorsPickOrder ?? 0,
  });
}

export function mergeAcademyCategories(
  cms: CmsAcademyCategoryDoc[] | null | undefined,
): AcademyCategory[] {
  if (!cms?.length) return [];
  return cms
    .map((doc) =>
      resolveSiteCopyDeep({
        slug: doc.slug,
        label: doc.label?.trim() || doc.slug,
        sortOrder: doc.sortOrder ?? 0,
      }),
    )
    .sort((a, b) => {
      const orderDiff = (b.sortOrder ?? 0) - (a.sortOrder ?? 0);
      if (orderDiff !== 0) return orderDiff;
      return a.label.localeCompare(b.label, "zh-CN");
    });
}

export function mergeAcademyList(cms: CmsAcademyDoc[] | null | undefined): AcademyListItem[] {
  if (!cms?.length) return [];

  const merged = cms.map(cmsDocToAcademyListItem);
  merged.sort((a, b) => {
    const orderDiff = (b.sortOrder ?? 0) - (a.sortOrder ?? 0);
    if (orderDiff !== 0) return orderDiff;
    const dateA = a.publishedAt ? Date.parse(a.publishedAt) : 0;
    const dateB = b.publishedAt ? Date.parse(b.publishedAt) : 0;
    return dateB - dateA;
  });
  return merged;
}

export function findAcademyListItem(
  items: AcademyListItem[],
  slug: string,
): AcademyListItem | undefined {
  return items.find((item) => item.slug === slug);
}
