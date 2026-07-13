import type { ResearchListItem } from "@shared/research";

import type { CmsSeoMeta } from "@/lib/seo";

export type CmsMediaRef = {
  url?: string | null;
  alt?: string | null;
  width?: number | null;
  height?: number | null;
};

export type CmsResearchCategoryDoc = {
  slug: string;
  label: string;
  sortOrder?: number | null;
};

export type CmsResearchDoc = {
  slug: string;
  category?: CmsResearchCategoryDoc | string | null;
  cardTitle: string;
  cardDescription: string;
  cardLabels?: string[] | null;
  cover?: CmsMediaRef | string | null;
  sortOrder?: number | null;
  publishedAt?: string | null;
  body?: Record<string, unknown> | null;
  meta?: CmsSeoMeta | null;
};

export function resolveResearchCategorySlug(
  category: CmsResearchDoc["category"],
  fallback = "industry",
): ResearchListItem["categorySlug"] {
  if (!category) return fallback;
  if (typeof category === "string") return fallback;
  return category.slug?.trim() || fallback;
}
