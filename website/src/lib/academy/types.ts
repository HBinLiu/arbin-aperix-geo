import type { CmsSeoMeta } from "@/lib/seo";

export type CmsAcademyMedia = {
  url?: string | null;
  alt?: string | null;
  width?: number | null;
  height?: number | null;
};

export type CmsAcademyCategoryRef =
  | number
  | string
  | {
      id?: number | string;
      slug?: string | null;
      label?: string | null;
    }
  | null;

export type CmsAcademyCategoryDoc = {
  slug: string;
  label: string;
  sortOrder?: number | null;
};

export type CmsAcademyDoc = {
  slug: string;
  cardTitle: string;
  cardDescription: string;
  tag?: string | null;
  cover?: CmsAcademyMedia | null;
  category?: CmsAcademyCategoryRef;
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
