import { chartColorForKey } from "@/lib/analysis/chart";

/** 按品牌名取稳定色（与 chartColorForKey 一致，仅首字母占位时使用） */
export function brandIconColor(label: string): string {
  return chartColorForKey(label.trim() || "?");
}

/** favicon 目标：优先 domain，否则用展示名 */
export function brandIconFaviconLabel(displayLabel: string, domain?: string | null): string {
  return (domain ?? "").trim() || displayLabel.trim();
}
