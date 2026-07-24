import { getPageItems, parseListPage } from "@/lib/pagination";

/** 与 reference research 列表页一致：3 列 × 2 行 */
export const RESEARCH_LIST_PAGE_SIZE = 6;

export const getResearchPageItems = getPageItems;

export function buildResearchListUrl(page: number, category: string = "all"): string {
  const params = new URLSearchParams();
  if (page > 1) params.set("page", String(page));
  if (category !== "all") params.set("category", category);
  const query = params.toString();
  return query ? `/research/?${query}` : "/research/";
}

export const parseResearchListPage = parseListPage;

export function parseResearchListCategory(value: string | null | undefined): string {
  return value?.trim() || "all";
}

/** 读取 URL 筛选分类；兼容旧版 ?tag= */
export function readResearchListCategory(params: URLSearchParams): string {
  return parseResearchListCategory(params.get("category") ?? params.get("tag"));
}
