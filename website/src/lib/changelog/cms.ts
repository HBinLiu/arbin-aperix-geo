import {
  CHANGELOG_RELEASE_TYPE_LABELS,
  type ChangelogAuthorSummary,
  type ChangelogListItem,
  type ChangelogReleaseType,
} from "@shared/changelog";
import type { CmsChangelogAuthorRef, CmsChangelogDoc } from "@/lib/changelog/types";
import { resolveChangelogMediaUrl } from "@/lib/changelog/media";
import { resolveSiteCopyDeep } from "@/lib/site";

function normalizeReleaseType(value: string | null | undefined): ChangelogReleaseType {
  if (value === "fix" || value === "improvement" || value === "feature") return value;
  return "feature";
}

function resolveAuthorSummary(
  author: CmsChangelogAuthorRef | undefined,
): ChangelogAuthorSummary | undefined {
  if (!author || typeof author === "number" || typeof author === "string") {
    return undefined;
  }
  const slug = author.slug?.trim();
  const name = author.name?.trim();
  if (!slug || !name) return undefined;
  const avatar =
    author.avatar && typeof author.avatar === "object" ? author.avatar : null;
  return {
    slug,
    name,
    avatarUrl: resolveChangelogMediaUrl(avatar) || undefined,
    bio: author.bio?.trim() || undefined,
  };
}

export function cmsDocToChangelogListItem(doc: CmsChangelogDoc): ChangelogListItem {
  return resolveSiteCopyDeep({
    slug: doc.slug,
    cardTitle: doc.cardTitle?.trim() || doc.slug,
    cardDescription: doc.cardDescription?.trim() || "",
    version: doc.version?.trim() || undefined,
    releaseType: normalizeReleaseType(doc.releaseType),
    author: resolveAuthorSummary(doc.author),
    publishedAt: doc.publishedAt,
    updatedAt: doc.updatedAt ?? doc.publishedAt,
    readMinutes: doc.readMinutes ?? 5,
    sortOrder: doc.sortOrder ?? 0,
  });
}

export function mergeChangelogList(
  cms: CmsChangelogDoc[] | null | undefined,
): ChangelogListItem[] {
  if (!cms?.length) return [];

  const merged = cms.map(cmsDocToChangelogListItem);
  merged.sort((a, b) => {
    const orderDiff = (b.sortOrder ?? 0) - (a.sortOrder ?? 0);
    if (orderDiff !== 0) return orderDiff;
    const dateA = a.publishedAt ? Date.parse(a.publishedAt) : 0;
    const dateB = b.publishedAt ? Date.parse(b.publishedAt) : 0;
    return dateB - dateA;
  });
  return merged;
}

export function findChangelogListItem(
  items: ChangelogListItem[],
  slug: string,
): ChangelogListItem | undefined {
  return items.find((item) => item.slug === slug);
}

export function releaseTypeLabel(type: ChangelogReleaseType): string {
  return CHANGELOG_RELEASE_TYPE_LABELS[type];
}
