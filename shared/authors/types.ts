import type { SocialPlatform } from "../social";

/** 作者社交链接（平台选项与 SiteFooter 一致） */
export type AuthorSocialLink = {
  platform: SocialPlatform;
  url: string;
};

/** 作者资料（作者页 Hero） */
export type AuthorProfile = {
  slug: string;
  name: string;
  avatarUrl?: string;
  bio: string;
  socialLinks: AuthorSocialLink[];
  sortOrder?: number;
};
