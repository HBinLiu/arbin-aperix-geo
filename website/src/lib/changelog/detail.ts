import {
  changelogSidebarDefault,
  type ChangelogHeroDetail,
  type ChangelogListItem,
  type ChangelogSidebarCta,
  type ChangelogTocItem,
} from "@shared/changelog";
import type { AuthorProfile } from "@shared/authors";
import { resolveAppLink } from "@/lib/app-links";
import { changelogRichTextToHtml } from "@/lib/changelog/body";
import { extractChangelogToc } from "@/lib/changelog/toc";
import type { CmsChangelogDoc } from "@/lib/changelog/types";
import { releaseTypeLabel } from "@/lib/changelog/cms";
import { resolveSiteCopyDeep } from "@/lib/site";

export type ChangelogDetailViewModel = {
  listItem: ChangelogListItem;
  hero: ChangelogHeroDetail;
  author: AuthorProfile | null;
  sidebar: ChangelogSidebarCta;
  toc: ChangelogTocItem[];
  bodyHtml: string;
  hasBody: boolean;
};

/** 详情「更新于」：2026年7月15日 */
export function formatChangelogDetailDate(value: string | undefined): string {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return new Intl.DateTimeFormat("zh-CN", {
    year: "numeric",
    month: "long",
    day: "numeric",
  }).format(date);
}

/** 列表卡片日期：2026年7月16日 */
export function formatChangelogListDate(value: string | undefined): string {
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
  listAuthor: ChangelogListItem["author"],
  fullAuthor: AuthorProfile | null | undefined,
): ChangelogHeroDetail["author"] {
  if (fullAuthor) {
    return {
      slug: fullAuthor.slug,
      name: fullAuthor.name,
      avatarUrl: fullAuthor.avatarUrl || listAuthor?.avatarUrl,
      bio: fullAuthor.bio || listAuthor?.bio,
    };
  }
  return listAuthor;
}

function buildChangelogHero(
  listItem: ChangelogListItem,
  cmsDoc: CmsChangelogDoc | null | undefined,
  fullAuthor?: AuthorProfile | null,
): ChangelogHeroDetail {
  const readMinutes =
    cmsDoc?.readMinutes && cmsDoc.readMinutes > 0
      ? cmsDoc.readMinutes
      : listItem.readMinutes && listItem.readMinutes > 0
        ? listItem.readMinutes
        : 5;

  return resolveSiteCopyDeep({
    title: listItem.cardTitle,
    version: listItem.version,
    releaseType: listItem.releaseType,
    releaseTypeLabel: releaseTypeLabel(listItem.releaseType),
    author: resolveHeroAuthor(listItem.author, fullAuthor),
    readMinutes,
    readTimeLabel: `${readMinutes} 分钟阅读`,
    updatedLabel: formatChangelogDetailDate(listItem.updatedAt || listItem.publishedAt),
  });
}

export function buildChangelogDetail(
  listItem: ChangelogListItem,
  cmsDoc: CmsChangelogDoc | null | undefined,
  options?: {
    author?: AuthorProfile | null;
  },
): ChangelogDetailViewModel {
  const body = cmsDoc?.body ?? null;
  const bodyHtml = changelogRichTextToHtml(body);
  const hasBody = bodyHtml.trim().length > 0;
  const sidebar: ChangelogSidebarCta = resolveSiteCopyDeep({
    ...changelogSidebarDefault,
    primaryHref: resolveAppLink(changelogSidebarDefault.primaryHref),
  });

  return resolveSiteCopyDeep({
    listItem,
    hero: buildChangelogHero(listItem, cmsDoc, options?.author),
    author: options?.author ?? null,
    sidebar,
    toc: extractChangelogToc(body),
    bodyHtml,
    hasBody,
  });
}
