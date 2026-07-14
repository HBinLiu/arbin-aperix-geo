import type { CmsSeoMeta } from "@/lib/seo";

export type CmsBlogMedia = {
  url?: string | null;
  alt?: string | null;
  width?: number | null;
  height?: number | null;
};

export type CmsBlogCategoryRef =
  | number
  | string
  | {
      id?: number | string;
      slug?: string | null;
      label?: string | null;
    }
  | null;

export type CmsBlogAuthorRef =
  | number
  | string
  | {
      id?: number | string;
      slug?: string | null;
      name?: string | null;
      avatar?: CmsBlogMedia | number | string | null;
      bio?: string | null;
      socialLinks?: Array<{
        platform?: string | null;
        url?: string | null;
      }> | null;
    }
  | null;

export type CmsBlogCategoryDoc = {
  slug: string;
  label: string;
  sortOrder?: number | null;
};

export type CmsBlogDoc = {
  slug: string;
  cardTitle: string;
  cardDescription: string;
  cover?: CmsBlogMedia | null;
  category?: CmsBlogCategoryRef;
  author?: CmsBlogAuthorRef;
  readMinutes?: number | null;
  publishedAt: string;
  updatedAt?: string | null;
  sortOrder?: number | null;
  isFeatured?: boolean | null;
  isEditorsPick?: boolean | null;
  editorsPickOrder?: number | null;
  body?: Record<string, unknown> | null;
  meta?: CmsSeoMeta | null;
};
