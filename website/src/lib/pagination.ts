/** 页码窗：≤7 全显示，否则 1 … 邻页 … 末页 */
export function getPageItems(
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

export function parseListPage(value: string | null | undefined): number {
  const parsed = Number.parseInt(value ?? "1", 10);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : 1;
}
