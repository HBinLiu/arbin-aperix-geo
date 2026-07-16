export type {
  ChangelogAuthorSummary,
  ChangelogHeroDetail,
  ChangelogListItem,
  ChangelogReleaseType,
  ChangelogSidebarCta,
  ChangelogTocItem,
} from "@shared/changelog";
export { changelogListHero, changelogSidebarDefault } from "@shared/changelog";

export function changelogHref(slug: string): string {
  return `/changelogs/${slug}/`;
}

export function authorHref(slug: string): string {
  return `/authors/${slug}/`;
}
