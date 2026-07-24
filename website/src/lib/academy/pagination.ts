import { getPageItems, parseListPage } from "@/lib/pagination";

/** 与博客列表一致：3 列 × 2 行 */
export const ACADEMY_LIST_PAGE_SIZE = 6;

export const getAcademyPageItems = getPageItems;

export function buildAcademyListUrl(
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
  return query ? `/academy/?${query}` : "/academy/";
}

export const parseAcademyListPage = parseListPage;

export function parseAcademyListCategory(params: URLSearchParams | string | null | undefined): string {
  if (typeof params === "string" || params == null) {
    return params?.trim() || "all";
  }
  return params.get("category")?.trim() || "all";
}

export function parseAcademyListSearch(params: URLSearchParams | string | null | undefined): string {
  if (typeof params === "string" || params == null) {
    return params?.trim() || "";
  }
  return params.get("s")?.trim() || "";
}

export function paginateAcademyPosts<T>(
  items: T[],
  page: number,
  pageSize: number = ACADEMY_LIST_PAGE_SIZE,
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
