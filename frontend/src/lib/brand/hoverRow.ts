import { faviconUrlFromHost } from "@/lib/favicon";
import type { CompetitorItem, Subject } from "@/types";

/**
 * 悬停卡品牌解析。
 * 配置竞品/自有品牌优先按 label 匹配；开集行用 hints.domain 补全 favicon。
 */

const DOMAIN_LABEL = /\.[a-z]{2,}/i;

export type BrandHoverHints = {
  /** 开集/排行列表 API 提供的 domain，用于 favicon 与悬停卡一致 */
  domain?: string | null;
  summary?: string | null;
};

export function brandRowLabel(row: Pick<CompetitorItem, "brand" | "domain">): string {
  return row.brand.trim() || row.domain;
}

function normalize(value: string): string {
  return value.trim().toLowerCase();
}

function matchesLabel(label: string, item: Pick<CompetitorItem, "brand" | "domain" | "aliases">): boolean {
  const target = normalize(label);
  if (!target) return false;
  if (normalize(brandRowLabel(item)) === target) return true;
  if (item.domain && normalize(item.domain) === target) return true;
  if (item.brand.trim() && normalize(item.brand) === target) return true;
  for (const alias of item.aliases ?? []) {
    if (normalize(alias) === target) return true;
  }
  return false;
}

function withWebsiteUrl(row: CompetitorItem): CompetitorItem {
  if (row.website_url.trim()) return row;
  const domain = row.domain.trim();
  if (!domain) return row;
  return { ...row, website_url: faviconUrlFromHost(domain) };
}

/** 将列表侧 domain/summary 补全到已解析行，不覆盖已有配置字段。 */
function applyHoverHints(row: CompetitorItem, hints?: BrandHoverHints): CompetitorItem {
  if (!hints) return withWebsiteUrl(row);

  const domain = (row.domain.trim() || (hints.domain ?? "").trim());
  const summary = (row.summary.trim() || (hints.summary ?? "").trim());
  const website_url = row.website_url.trim() || (domain ? faviconUrlFromHost(domain) : "");

  return withWebsiteUrl({
    ...row,
    domain,
    website_url,
    summary,
  });
}

function subjectAsHoverRow(subject: Subject): CompetitorItem {
  return withWebsiteUrl({
    domain: subject.domain,
    website_url: subject.website_url,
    brand: subject.brand,
    summary: subject.summary,
  });
}

function synthesizeOpenSetRow(label: string, hints?: BrandHoverHints): CompetitorItem {
  const domainHint = (hints?.domain ?? "").trim();
  const trimmed = label.trim();

  if (domainHint) {
    return withWebsiteUrl({
      domain: domainHint,
      website_url: "",
      brand: trimmed,
      summary: (hints?.summary ?? "").trim(),
    });
  }

  if (DOMAIN_LABEL.test(trimmed)) {
    return withWebsiteUrl({
      domain: trimmed,
      website_url: "",
      brand: "",
      summary: (hints?.summary ?? "").trim(),
    });
  }

  return {
    domain: "",
    website_url: "",
    brand: trimmed,
    summary: (hints?.summary ?? "").trim(),
  };
}

/**
 * 解析悬停卡数据：配置竞品 → 自有品牌 → 开集合成。
 * hints.domain 仅补全开集/排行行，不会跳过配置竞品匹配。
 */
export function resolveBrandHoverRow(
  label: string,
  subject: Subject,
  competitors: CompetitorItem[],
  hints?: BrandHoverHints,
): CompetitorItem {
  for (const item of competitors) {
    if (matchesLabel(label, item)) {
      return applyHoverHints(item, hints);
    }
  }

  const own = subjectAsHoverRow(subject);
  if (matchesLabel(label, own)) {
    return applyHoverHints(own, hints);
  }

  return applyHoverHints(synthesizeOpenSetRow(label, hints), hints);
}
