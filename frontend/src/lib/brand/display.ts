import { buildBrandRankIcon, type BrandRankIconProps } from "@/components/analysis/common/BrandRankIcon";
import { brandIconFaviconLabel } from "@/lib/brand/iconColor";
import { externalHref } from "@/lib/domain";
import { faviconUrlFromWebsite } from "@/lib/favicon";
import type { CompetitorItem } from "@/types";
import type { ReactNode } from "react";

type BrandVisual = Pick<CompetitorItem, "website_url" | "domain">;

type BrandListIconOptions = Pick<
  BrandRankIconProps,
  "size" | "shape" | "faviconLoadingSpinner"
>;

/** 展示名：brand → label → domain */
export function brandDisplayLabel(parts: {
  brand?: string | null;
  label?: string | null;
  domain?: string | null;
}): string {
  return (
    parts.brand?.trim() ||
    parts.label?.trim() ||
    parts.domain?.trim() ||
    ""
  );
}

/** 表格「提及品牌」列 tooltip / 列表文案 */
export function mentionedBrandDisplayLabel(brand: {
  brand?: string | null;
  label: string;
  domain?: string | null;
}): string {
  return brandDisplayLabel(brand);
}

/** 列表行品牌图标：优先 domain favicon；无 favicon 时首字母着色。 */
export function brandListIcon(
  label: string,
  domain?: string | null,
  options?: BrandListIconOptions,
): ReactNode | undefined {
  const displayLabel = label.trim();
  if (!displayLabel && !(domain ?? "").trim()) return undefined;
  return buildBrandRankIcon(brandIconFaviconLabel(displayLabel, domain), options);
}

/** 悬停卡 / 配置竞品：优先 website_url，否则 domain。 */
export function brandFaviconUrl(row: BrandVisual): string | null {
  return faviconUrlFromWebsite(row.website_url, row.domain);
}

/** 可点击外链：保留 http(s)；裸 host 用 http://（不强制 https）。 */
export function brandWebsiteUrl(row: BrandVisual): string | null {
  const url = row.website_url?.trim();
  if (url) return externalHref(url);
  const domain = row.domain?.trim();
  if (domain) return externalHref(domain);
  return null;
}
