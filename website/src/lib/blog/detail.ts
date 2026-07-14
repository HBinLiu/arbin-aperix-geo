import {
  blogSidebarDefault,
  type BlogHeroDetail,
  type BlogListItem,
  type BlogSidebarCta,
  type BlogTocItem,
} from "@shared/blog";
import type { AuthorProfile } from "@shared/authors";
import { appLinks, resolveAppLink } from "@/lib/app-links";
import { blogRichTextToHtml } from "@/lib/blog/body";
import { extractBlogToc } from "@/lib/blog/toc";
import type { CmsBlogDoc } from "@/lib/blog/types";
import { resolveSiteCopyDeep } from "@/lib/site";

export type BlogDetailViewModel = {
  listItem: BlogListItem;
  hero: BlogHeroDetail;
  author: AuthorProfile | null;
  relatedPosts: BlogListItem[];
  sidebar: BlogSidebarCta;
  toc: BlogTocItem[];
  bodyHtml: string;
  hasBody: boolean;
};

/** 详情「更新于」等：2026年7月15日 */
export function formatBlogCardDate(value: string | undefined): string {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return new Intl.DateTimeFormat("zh-CN", {
    year: "numeric",
    month: "long",
    day: "numeric",
  }).format(date);
}

function formatPublishedLabel(value: string | undefined): string {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return new Intl.DateTimeFormat("zh-CN", {
    year: "numeric",
    month: "long",
    day: "numeric",
  }).format(date);
}

function resolveHeroAuthor(
  listAuthor: BlogListItem["author"],
  fullAuthor: AuthorProfile | null | undefined,
): BlogHeroDetail["author"] {
  if (fullAuthor) {
    return {
      slug: fullAuthor.slug,
      name: fullAuthor.name,
      avatarUrl: fullAuthor.avatarUrl || listAuthor?.avatarUrl,
    };
  }
  return listAuthor;
}

function buildBlogHero(
  listItem: BlogListItem,
  cmsDoc: CmsBlogDoc | null | undefined,
  fullAuthor?: AuthorProfile | null,
): BlogHeroDetail {
  const readMinutes =
    cmsDoc?.readMinutes && cmsDoc.readMinutes > 0
      ? cmsDoc.readMinutes
      : listItem.readMinutes && listItem.readMinutes > 0
        ? listItem.readMinutes
        : 5;

  return resolveSiteCopyDeep({
    title: listItem.cardTitle,
    lead: listItem.cardDescription,
    coverUrl: listItem.coverUrl,
    categoryLabel: listItem.categoryLabel,
    author: resolveHeroAuthor(listItem.author, fullAuthor),
    publishedLabel: formatPublishedLabel(listItem.publishedAt),
    updatedLabel: formatBlogCardDate(listItem.updatedAt || listItem.publishedAt),
    readMinutes,
    readTimeLabel: `${readMinutes} 分钟阅读`,
    primaryHref: appLinks.register,
    primaryLabel: "开始免费试用",
  });
}

/** 同分类优先，不足再用最新文章，最多 4 篇 */
export function pickRelatedBlogPosts(
  current: BlogListItem,
  all: BlogListItem[],
  limit = 4,
): BlogListItem[] {
  const others = all.filter((post) => post.slug !== current.slug);
  const sameCategory = current.categorySlug
    ? others.filter((post) => post.categorySlug === current.categorySlug)
    : [];
  const rest = others.filter((post) => !sameCategory.some((item) => item.slug === post.slug));
  return [...sameCategory, ...rest].slice(0, limit);
}

export function buildBlogDetail(
  listItem: BlogListItem,
  cmsDoc: CmsBlogDoc | null | undefined,
  options?: {
    author?: AuthorProfile | null;
    relatedPosts?: BlogListItem[];
  },
): BlogDetailViewModel {
  const body = cmsDoc?.body ?? null;
  const bodyHtml = blogRichTextToHtml(body);
  const hasBody = bodyHtml.trim().length > 0;
  const sidebar: BlogSidebarCta = resolveSiteCopyDeep({
    ...blogSidebarDefault,
    primaryHref: resolveAppLink(blogSidebarDefault.primaryHref),
  });

  return resolveSiteCopyDeep({
    listItem,
    hero: buildBlogHero(listItem, cmsDoc, options?.author),
    author: options?.author ?? null,
    relatedPosts: options?.relatedPosts ?? [],
    sidebar,
    toc: extractBlogToc(body),
    bodyHtml,
    hasBody,
  });
}
