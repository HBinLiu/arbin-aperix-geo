import type { AuthorProfile, AuthorSocialLink } from "@shared/authors";
import { SOCIAL_PLATFORM_VALUES, type SocialPlatform } from "@shared/social";
import type { CmsAuthorDoc } from "@/lib/authors/types";
import { resolveBlogMediaUrl } from "@/lib/blog/media";
import { resolveSiteCopyDeep } from "@/lib/site";

const allowedPlatforms = new Set<string>(SOCIAL_PLATFORM_VALUES);

function normalizeSocialLinks(
  links: CmsAuthorDoc["socialLinks"],
): AuthorSocialLink[] {
  if (!links?.length) return [];
  return links
    .map((link) => {
      const platform = link.platform?.trim();
      const url = link.url?.trim();
      if (!platform || !url || !allowedPlatforms.has(platform)) return null;
      return {
        platform: platform as SocialPlatform,
        url,
      };
    })
    .filter((link): link is AuthorSocialLink => Boolean(link));
}

export function cmsDocToAuthor(doc: CmsAuthorDoc): AuthorProfile {
  return resolveSiteCopyDeep({
    slug: doc.slug,
    name: doc.name?.trim() || doc.slug,
    avatarUrl: resolveBlogMediaUrl(doc.avatar) || undefined,
    bio: doc.bio?.trim() || "",
    socialLinks: normalizeSocialLinks(doc.socialLinks),
    sortOrder: doc.sortOrder ?? 0,
  });
}

export function mergeAuthors(cms: CmsAuthorDoc[] | null | undefined): AuthorProfile[] {
  if (!cms?.length) return [];
  return cms
    .map(cmsDocToAuthor)
    .sort((a, b) => {
      const orderDiff = (b.sortOrder ?? 0) - (a.sortOrder ?? 0);
      if (orderDiff !== 0) return orderDiff;
      return a.name.localeCompare(b.name, "zh-CN");
    });
}

export function findAuthor(
  authors: AuthorProfile[],
  slug: string,
): AuthorProfile | undefined {
  return authors.find((author) => author.slug === slug);
}
