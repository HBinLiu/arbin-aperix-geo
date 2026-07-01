import { buildBrandRankIcon } from "@/components/analysis/common/BrandRankIcon";
import { externalHref } from "@/lib/domain";
import { faviconUrlFromWebsite } from "@/lib/favicon";
import type { CompetitorItem } from "@/types";
import type { ReactNode } from "react";

type BrandVisual = Pick<CompetitorItem, "website_url" | "domain">;

/** 列表行 favicon：优先 domain，否则按 label 推断。 */
export function brandListIcon(label: string, domain?: string | null): ReactNode | undefined {
  return buildBrandRankIcon((domain ?? "").trim() || label);
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
