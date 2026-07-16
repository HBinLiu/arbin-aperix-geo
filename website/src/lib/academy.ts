export type {
  AcademyCategory,
  AcademyHeroDetail,
  AcademyListItem,
  AcademySidebarCta,
  AcademyTocItem,
} from "@shared/academy";
export { academySidebarDefault } from "@shared/academy";
export { ACADEMY_LIST_PAGE_SIZE } from "@/lib/academy/pagination";

export function academyHref(slug: string): string {
  return `/academy/${slug}/`;
}
