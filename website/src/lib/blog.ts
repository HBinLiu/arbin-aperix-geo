export type {
  BlogAuthorSummary,
  BlogCategory,
  BlogHeroDetail,
  BlogListItem,
  BlogSidebarCta,
  BlogTocItem,
} from "@shared/blog";
export { blogSidebarDefault } from "@shared/blog";
export { BLOG_LIST_PAGE_SIZE } from "@/lib/blog/pagination";

export function blogHref(slug: string): string {
  return `/blog/${slug}/`;
}

export function authorHref(slug: string): string {
  return `/authors/${slug}/`;
}
