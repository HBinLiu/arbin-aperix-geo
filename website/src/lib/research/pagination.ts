/** 与 reference research 列表页一致：3 列 × 2 行 */
export const RESEARCH_LIST_PAGE_SIZE = 6;

export function getResearchPageItems(
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

export function buildResearchListUrl(page: number, category: string = "all"): string {
  const params = new URLSearchParams();
  if (page > 1) params.set("page", String(page));
  if (category !== "all") params.set("category", category);
  const query = params.toString();
  return query ? `/research/?${query}` : "/research/";
}

export function parseResearchListPage(value: string | null | undefined): number {
  const parsed = Number.parseInt(value ?? "1", 10);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : 1;
}

export function parseResearchListCategory(value: string | null | undefined): string {
  return value?.trim() || "all";
}

/** 读取 URL 筛选分类；兼容旧版 ?tag= */
export function readResearchListCategory(params: URLSearchParams): string {
  return parseResearchListCategory(params.get("category") ?? params.get("tag"));
}
