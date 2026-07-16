import type { ChangelogReleaseType } from "@shared/changelog";
import type { CmsSeoMeta } from "@/lib/seo";

export type CmsChangelogMedia = {
  url?: string | null;
  alt?: string | null;
  width?: number | null;
  height?: number | null;
};

export type CmsChangelogAuthorRef =
  | number
  | string
  | {
      id?: number | string;
      slug?: string | null;
      name?: string | null;
      avatar?: CmsChangelogMedia | number | string | null;
      bio?: string | null;
      socialLinks?: Array<{
        platform?: string | null;
        url?: string | null;
      }> | null;
    }
  | null;

export type CmsChangelogDoc = {
  slug: string;
  cardTitle: string;
  cardDescription: string;
  version?: string | null;
  releaseType: ChangelogReleaseType;
  author?: CmsChangelogAuthorRef;
  readMinutes?: number | null;
  publishedAt: string;
  updatedAt?: string | null;
  sortOrder?: number | null;
  body?: Record<string, unknown> | null;
  meta?: CmsSeoMeta | null;
};
