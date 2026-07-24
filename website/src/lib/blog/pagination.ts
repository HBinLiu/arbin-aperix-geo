import { getPageItems, parseListPage } from "@/lib/pagination";

/** 与参考博客列表一致：3 列 × 2 行 */
export const BLOG_LIST_PAGE_SIZE = 6;

export const getBlogPageItems = getPageItems;

export function buildBlogListUrl(
  page: number,
  category: string = "all",
  search: string = "",
): string {
  const params = new URLSearchParams();
  if (page > 1) params.set("page", String(page));
  if (category !== "all") params.set("category", category);
  const q = search.trim();
  if (q) params.set("s", q);
  const query = params.toString();
  return query ? `/blog/?${query}` : "/blog/";
}

export function buildAuthorListUrl(authorSlug: string, page: number): string {
  const base = `/authors/${encodeURIComponent(authorSlug)}/`;
  if (page <= 1) return base;
  return `${base}?page=${page}`;
}

export const parseBlogListPage = parseListPage;

export function parseBlogListCategory(params: URLSearchParams | string | null | undefined): string {
  if (typeof params === "string" || params == null) {
    return params?.trim() || "all";
  }
  return params.get("category")?.trim() || "all";
}

export function parseBlogListSearch(params: URLSearchParams | string | null | undefined): string {
  if (typeof params === "string" || params == null) {
    return params?.trim() || "";
  }
  return params.get("s")?.trim() || "";
}

export function paginateBlogPosts<T>(
  items: T[],
  page: number,
  pageSize: number = BLOG_LIST_PAGE_SIZE,
): { items: T[]; page: number; totalPages: number; total: number } {
  const total = items.length;
  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  const safePage = Math.min(Math.max(page, 1), totalPages);
  const start = (safePage - 1) * pageSize;
  return {
    items: items.slice(start, start + pageSize),
    page: safePage,
    totalPages,
    total,
  };
}
