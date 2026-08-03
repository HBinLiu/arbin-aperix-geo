import {
  academySidebarDefault,
  type AcademyHeroDetail,
  type AcademyListItem,
  type AcademySidebarCta,
  type AcademyTocItem,
} from "@shared/academy";
import { appLinks, resolveAppLink } from "@/lib/app-links";
import { academyRichTextToHtml } from "@/lib/academy/body";
import { extractAcademyToc } from "@/lib/academy/toc";
import type { CmsAcademyDoc } from "@/lib/academy/types";
import { resolveSiteCopyDeep } from "@/lib/site";

export type AcademyDetailViewModel = {
  listItem: AcademyListItem;
  hero: AcademyHeroDetail;
  relatedPosts: AcademyListItem[];
  sidebar: AcademySidebarCta;
  toc: AcademyTocItem[];
  bodyHtml: string;
  hasBody: boolean;
};

/** 详情「更新于」等：2026年7月15日 */
export function formatAcademyCardDate(value: string | undefined): string {
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

function buildAcademyHero(
  listItem: AcademyListItem,
  cmsDoc: CmsAcademyDoc | null | undefined,
): AcademyHeroDetail {
  const readMinutes =
    cmsDoc?.readMinutes && cmsDoc.readMinutes > 0
      ? cmsDoc.readMinutes
      : listItem.readMinutes && listItem.readMinutes > 0
        ? listItem.readMinutes
        : 5;

  const tag =
    cmsDoc?.tag?.trim() ||
    listItem.tag?.trim() ||
    listItem.categoryLabel?.trim() ||
    "AI 可见性指南";

  return resolveSiteCopyDeep({
    tag,
    title: listItem.cardTitle,
    lead: listItem.cardDescription,
    coverUrl: listItem.coverUrl,
    categoryLabel: listItem.categoryLabel,
    publishedLabel: formatPublishedLabel(listItem.publishedAt),
    updatedLabel: formatAcademyCardDate(listItem.updatedAt || listItem.publishedAt),
    readMinutes,
    readTimeLabel: `${readMinutes} 分钟阅读`,
    primaryHref: appLinks.register,
    primaryLabel: "开始注册试用",
  });
}

/** 同分类优先，不足再用最新文章，最多 4 篇 */
export function pickRelatedAcademyPosts(
  current: AcademyListItem,
  all: AcademyListItem[],
  limit = 4,
): AcademyListItem[] {
  const others = all.filter((post) => post.slug !== current.slug);
  const sameCategory = current.categorySlug
    ? others.filter((post) => post.categorySlug === current.categorySlug)
    : [];
  const rest = others.filter((post) => !sameCategory.some((item) => item.slug === post.slug));
  return [...sameCategory, ...rest].slice(0, limit);
}

export function buildAcademyDetail(
  listItem: AcademyListItem,
  cmsDoc: CmsAcademyDoc | null | undefined,
  options?: {
    relatedPosts?: AcademyListItem[];
  },
): AcademyDetailViewModel {
  const body = cmsDoc?.body ?? null;
  const bodyHtml = academyRichTextToHtml(body);
  const hasBody = bodyHtml.trim().length > 0;
  const sidebar: AcademySidebarCta = resolveSiteCopyDeep({
    ...academySidebarDefault,
    primaryHref: resolveAppLink(academySidebarDefault.primaryHref),
  });

  return resolveSiteCopyDeep({
    listItem,
    hero: buildAcademyHero(listItem, cmsDoc),
    relatedPosts: options?.relatedPosts ?? [],
    sidebar,
    toc: extractAcademyToc(body),
    bodyHtml,
    hasBody,
  });
}
