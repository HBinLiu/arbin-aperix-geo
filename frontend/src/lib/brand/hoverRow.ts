import type { CompetitorItem, Subject } from "@/types";

const DOMAIN_LABEL = /\.[a-z]{2,}/i;

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

function subjectAsHoverRow(subject: Subject): CompetitorItem {
  return {
    domain: subject.domain,
    website_url: subject.website_url,
    brand: subject.brand,
    summary: subject.summary,
  };
}

/** 按展示名解析悬停卡数据：竞品 → 自有品牌 → 按 label 合成。 */
export function resolveBrandHoverRow(
  label: string,
  subject: Subject,
  competitors: CompetitorItem[],
): CompetitorItem {
  for (const item of competitors) {
    if (matchesLabel(label, item)) return item;
  }

  const own = subjectAsHoverRow(subject);
  if (matchesLabel(label, own)) return own;

  const trimmed = label.trim();
  if (DOMAIN_LABEL.test(trimmed)) {
    return {
      domain: trimmed,
      website_url: "",
      brand: "",
      summary: "",
    };
  }

  return {
    domain: "",
    website_url: "",
    brand: trimmed,
    summary: "",
  };
}
