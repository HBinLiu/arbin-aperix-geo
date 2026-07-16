/** 更新日志发布类型 */
export type ChangelogReleaseType = "feature" | "fix" | "improvement";

export const CHANGELOG_RELEASE_TYPE_LABELS: Record<ChangelogReleaseType, string> = {
  feature: "Feature",
  fix: "Fix",
  improvement: "Improvement",
};

export type ChangelogAuthorSummary = {
  slug: string;
  name: string;
  avatarUrl?: string;
  bio?: string;
};

export type ChangelogListItem = {
  slug: string;
  cardTitle: string;
  cardDescription: string;
  version?: string;
  releaseType: ChangelogReleaseType;
  author?: ChangelogAuthorSummary;
  publishedAt?: string;
  updatedAt?: string;
  readMinutes?: number;
  sortOrder?: number;
};

export type ChangelogHeroDetail = {
  title: string;
  version?: string;
  releaseType: ChangelogReleaseType;
  releaseTypeLabel: string;
  author?: ChangelogAuthorSummary;
  readMinutes?: number;
  readTimeLabel?: string;
  updatedLabel?: string;
};

export type ChangelogTocItem = {
  id: string;
  label: string;
};

export type ChangelogSidebarCta = {
  title: string;
  items: string[];
  description?: string;
  primaryLabel: string;
  primaryHref: string;
};
