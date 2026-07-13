import type { CmsSeoMeta } from "@/lib/seo";

export type CmsNewsDoc = {
  slug: string;
  cardTitle: string;
  cardDescription: string;
  sortOrder?: number | null;
  publishedAt: string;
  tag?: string | null;
  sourceAuthor?: string | null;
  sourceUrl?: string | null;
  sourceLabel?: string | null;
  readMinutes?: number | null;
  editorNote?: string | null;
  body?: Record<string, unknown> | null;
  meta?: CmsSeoMeta | null;
};
