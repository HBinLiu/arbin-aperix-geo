import type { NewsListItem, NewsMonthGroup } from "@shared/news";

function monthKey(publishedAt: string | undefined): string {
  if (!publishedAt) return "unknown";
  const date = new Date(publishedAt);
  if (Number.isNaN(date.getTime())) return "unknown";
  return `${date.getUTCFullYear()}-${String(date.getUTCMonth() + 1).padStart(2, "0")}`;
}

function monthLabel(publishedAt: string | undefined): string {
  if (!publishedAt) return "未标注日期";
  const date = new Date(publishedAt);
  if (Number.isNaN(date.getTime())) return "未标注日期";
  return `${date.getUTCFullYear()}年${date.getUTCMonth() + 1}月`;
}

function publishedAtMs(publishedAt: string | undefined): number {
  if (!publishedAt) return 0;
  const ms = Date.parse(publishedAt);
  return Number.isNaN(ms) ? 0 : ms;
}

/** 按发布月份分组（旧月份在前）；组内按发布日期倒序 */
export function groupNewsByMonth(items: NewsListItem[]): NewsMonthGroup[] {
  const groups = new Map<string, NewsMonthGroup>();

  for (const item of items) {
    const key = monthKey(item.publishedAt);
    const existing = groups.get(key);
    if (existing) {
      existing.items.push(item);
      continue;
    }
    groups.set(key, {
      key,
      label: monthLabel(item.publishedAt),
      items: [item],
    });
  }

  for (const group of groups.values()) {
    group.items.sort(
      (a, b) => publishedAtMs(b.publishedAt) - publishedAtMs(a.publishedAt),
    );
  }

  return [...groups.values()].sort((a, b) => a.key.localeCompare(b.key));
}

export const NEWS_LIST_INITIAL_VISIBLE = 5;
