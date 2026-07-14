import type { CmsSeoMeta } from "@/lib/seo";
import type { CmsBlogMedia } from "@/lib/blog/types";

export type CmsAuthorDoc = {
  slug: string;
  name: string;
  avatar?: CmsBlogMedia | null;
  bio: string;
  socialLinks?: Array<{
    platform?: string | null;
    url?: string | null;
  }> | null;
  sortOrder?: number | null;
  meta?: CmsSeoMeta | null;
};
