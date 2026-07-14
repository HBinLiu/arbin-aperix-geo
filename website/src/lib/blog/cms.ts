import type { BlogAuthorSummary, BlogCategory, BlogListItem } from "@shared/blog";
import type { CmsBlogAuthorRef, CmsBlogCategoryDoc, CmsBlogCategoryRef, CmsBlogDoc } from "@/lib/blog/types";
import { resolveBlogMediaUrl } from "@/lib/blog/media";
import { resolveSiteCopyDeep } from "@/lib/site";

function resolveCategory(
  category: CmsBlogCategoryRef | undefined,
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

function resolveAuthorSummary(author: CmsBlogAuthorRef | undefined): BlogAuthorSummary | undefined {
  if (!author || typeof author === "number" || typeof author === "string") {
    return undefined;
  }
  const slug = author.slug?.trim();
  const name = author.name?.trim();
  if (!slug || !name) return undefined;
  const avatar =
    author.avatar && typeof author.avatar === "object" ? author.avatar : null;
  return {
    slug,
    name,
    avatarUrl: resolveBlogMediaUrl(avatar) || undefined,
  };
}

export function cmsDocToBlogListItem(doc: CmsBlogDoc): BlogListItem {
  const category = resolveCategory(doc.category);
  return resolveSiteCopyDeep({
    slug: doc.slug,
    cardTitle: doc.cardTitle?.trim() || doc.slug,
    cardDescription: doc.cardDescription?.trim() || "",
    coverUrl: resolveBlogMediaUrl(doc.cover ?? null) || undefined,
    categorySlug: category.slug,
    categoryLabel: category.label,
    author: resolveAuthorSummary(doc.author),
    publishedAt: doc.publishedAt,
    updatedAt: doc.updatedAt ?? doc.publishedAt,
    readMinutes: doc.readMinutes ?? 5,
    sortOrder: doc.sortOrder ?? 0,
    isFeatured: Boolean(doc.isFeatured),
    isEditorsPick: Boolean(doc.isEditorsPick),
    editorsPickOrder: doc.editorsPickOrder ?? 0,
  });
}

export function mergeBlogCategories(
  cms: CmsBlogCategoryDoc[] | null | undefined,
): BlogCategory[] {
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

export function mergeBlogList(cms: CmsBlogDoc[] | null | undefined): BlogListItem[] {
  if (!cms?.length) return [];

  const merged = cms.map(cmsDocToBlogListItem);
  merged.sort((a, b) => {
    const orderDiff = (b.sortOrder ?? 0) - (a.sortOrder ?? 0);
    if (orderDiff !== 0) return orderDiff;
    const dateA = a.publishedAt ? Date.parse(a.publishedAt) : 0;
    const dateB = b.publishedAt ? Date.parse(b.publishedAt) : 0;
    return dateB - dateA;
  });
  return merged;
}

export function findBlogListItem(
  items: BlogListItem[],
  slug: string,
): BlogListItem | undefined {
  return items.find((item) => item.slug === slug);
}
