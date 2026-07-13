import { newsSidebarDefault, type NewsHeroDetail, type NewsListItem, type NewsSidebarCta, type NewsTocItem } from "@shared/news";
import type { CmsNewsDoc } from "@/lib/news/types";
import { newsRichTextToHtml } from "@/lib/news/body";
import { extractNewsToc } from "@/lib/news/toc";
import { resolveSiteCopyDeep } from "@/lib/site";

export type NewsDetailViewModel = {
  listItem: NewsListItem;
  hero: NewsHeroDetail;
  sidebar: NewsSidebarCta;
  toc: NewsTocItem[];
  bodyHtml: string;
  hasBody: boolean;
};

function formatPublishedLabel(publishedAt: string | undefined): string {
  if (!publishedAt) return "";
  const date = new Date(publishedAt);
  if (Number.isNaN(date.getTime())) return "";
  return new Intl.DateTimeFormat("zh-CN", {
    year: "numeric",
    month: "long",
    day: "numeric",
  }).format(date);
}

function resolveSourceLabel(sourceUrl: string | undefined, sourceLabel: string | null | undefined): string {
  const label = sourceLabel?.trim();
  if (label) return label;
  const url = sourceUrl?.trim();
  if (!url) return "";
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return url;
  }
}

function buildNewsHero(listItem: NewsListItem, cmsDoc: CmsNewsDoc | null | undefined): NewsHeroDetail {
  const readMinutes = cmsDoc?.readMinutes && cmsDoc.readMinutes > 0 ? cmsDoc.readMinutes : 5;
  const sourceUrl = cmsDoc?.sourceUrl?.trim() ?? "";

  return resolveSiteCopyDeep({
    tag: cmsDoc?.tag?.trim() || "GEO 新闻简报 · AI 可见性",
    title: listItem.cardTitle,
    lead: cmsDoc?.cardDescription?.trim() || listItem.cardDescription,
    sourceAuthor: cmsDoc?.sourceAuthor?.trim() || "",
    sourceUrl,
    sourceLabel: resolveSourceLabel(sourceUrl, cmsDoc?.sourceLabel),
    publishedLabel: formatPublishedLabel(listItem.publishedAt),
    readMinutes,
    readTimeLabel: `${readMinutes} 分钟`,
    editorNote: cmsDoc?.editorNote?.trim() || "",
    primaryHref: "/auth/register",
    primaryLabel: "开始免费试用",
  });
}

export function buildNewsDetail(
  listItem: NewsListItem,
  cmsDoc: CmsNewsDoc | null | undefined,
): NewsDetailViewModel {
  const body = cmsDoc?.body ?? null;
  const bodyHtml = newsRichTextToHtml(body);
  const hasBody = bodyHtml.trim().length > 0;

  return resolveSiteCopyDeep({
    listItem,
    hero: buildNewsHero(listItem, cmsDoc),
    sidebar: newsSidebarDefault,
    toc: extractNewsToc(body),
    bodyHtml,
    hasBody,
  });
}
