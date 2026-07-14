/** 与参考博客列表一致：3 列 × 2 行 */
export const BLOG_LIST_PAGE_SIZE = 6;

export function getBlogPageItems(
  current: number,
  totalPages: number,
): (number | "ellipsis")[] {
  if (totalPages <= 7) {
    return Array.from({ length: totalPages }, (_, index) => index + 1);
  }

  const items: (number | "ellipsis")[] = [1];
  if (current > 3) items.push("ellipsis");

  const start = Math.max(2, current - 1);
  const end = Math.min(totalPages - 1, current + 1);
  for (let page = start; page <= end; page += 1) {
    items.push(page);
  }

  if (current < totalPages - 2) items.push("ellipsis");
  items.push(totalPages);
  return items;
}

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

export function parseBlogListPage(value: string | null | undefined): number {
  const parsed = Number.parseInt(value ?? "1", 10);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : 1;
}

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
