import { DEFAULT_MAX_COMPETITORS } from "@/lib/billing/limits";
import { coalesceWebsiteUrl, hostnameFromWebsiteInput, registrableDomain } from "@/lib/domain";
import type { CompetitorItem, CompetitorRow, DiscoveredCompetitor, SubjectMode } from "@/types";

export function newCompetitorRow(partial?: Partial<CompetitorRow>): CompetitorRow {
  return {
    id: crypto.randomUUID(),
    name: "",
    domain: "",
    websiteUrl: "",
    summary: "",
    aliases: [],
    selected: true,
    ...partial,
  };
}

export function rowsFromDiscover(
  competitors: DiscoveredCompetitor[],
  maxCount: number = DEFAULT_MAX_COMPETITORS,
): CompetitorRow[] {
  const safeMax = Math.max(1, maxCount);
  return competitors.slice(0, safeMax).map((c) =>
    newCompetitorRow({
      name: c.brand.trim() || (c.domain ? registrableDomain(c.domain) : ""),
      domain: c.domain ? registrableDomain(c.domain) : "",
      websiteUrl: (c.website_url ?? "").trim(),
      selected: true,
    }),
  );
}

/** 表格行主域名键（与 rowsToPersist 域名模式一致） */
export function competitorRowDomainKey(row: CompetitorRow): string {
  const raw = (row.domain || row.websiteUrl || row.name).trim();
  return registrableDomain(raw);
}

export type SubjectIdentity = {
  mode: SubjectMode;
  brand?: string;
  domain?: string;
  websiteUrl?: string;
  aliases?: string[];
};

export type CompetitorDuplicateKind = "domain" | "brand" | "self";

function subjectDomainKey(subject: SubjectIdentity): string {
  return registrableDomain((subject.domain || subject.websiteUrl || "").trim());
}

function subjectBrandKeys(subject: SubjectIdentity): string[] {
  const keys = new Set<string>();
  const brand = (subject.brand || "").trim().toLowerCase();
  if (brand) keys.add(brand);
  for (const alias of subject.aliases ?? []) {
    const key = alias.trim().toLowerCase();
    if (key) keys.add(key);
  }
  return [...keys];
}

/** 候选竞品是否与监测主体本身冲突 */
export function matchesSubjectIdentity(
  mode: SubjectMode,
  subject: SubjectIdentity,
  candidate: { name: string; domain: string },
): boolean {
  const nameKey = candidate.name.trim().toLowerCase();
  const domainKey = registrableDomain(candidate.domain);
  const subjectDomain = subjectDomainKey(subject);

  if (mode === "domain") {
    return domainKey.length >= 3 && subjectDomain.length >= 3 && domainKey === subjectDomain;
  }

  const brandKeys = subjectBrandKeys(subject);
  if (nameKey && brandKeys.includes(nameKey)) return true;
  return domainKey.length >= 3 && subjectDomain.length >= 3 && domainKey === subjectDomain;
}

export function findCompetitorDuplicate(
  mode: SubjectMode,
  rows: CompetitorRow[],
  candidate: { name: string; domain: string },
  subject?: SubjectIdentity,
): CompetitorDuplicateKind | null {
  if (subject && matchesSubjectIdentity(mode, subject, candidate)) {
    return "self";
  }

  const nameKey = candidate.name.trim().toLowerCase();
  const domainKey = registrableDomain(candidate.domain);

  if (mode === "domain") {
    if (domainKey.length >= 3 && rows.some((r) => competitorRowDomainKey(r) === domainKey)) {
      return "domain";
    }
    return null;
  }

  if (nameKey && rows.some((r) => r.name.trim().toLowerCase() === nameKey)) {
    return "brand";
  }
  if (domainKey.length >= 3 && rows.some((r) => competitorRowDomainKey(r) === domainKey)) {
    return "domain";
  }
  return null;
}

export function competitorDuplicateMessage(kind: CompetitorDuplicateKind): string {
  if (kind === "self") return "不能将监测主体添加为竞争对手。";
  if (kind === "brand") return "该竞品品牌已在列表中。";
  return "该竞品域名已在列表中。";
}

export function rowsToPersist(mode: SubjectMode, rows: CompetitorRow[]): { competitors: CompetitorItem[] } {
  const selected = rows.filter((r) => r.selected);
  if (mode === "domain") {
    const seen = new Set<string>();
    const competitors: CompetitorItem[] = [];
    for (const r of selected) {
      const rawInput = (r.domain || r.name).trim();
      const domain = registrableDomain(rawInput);
      if (domain.length < 3 || seen.has(domain)) continue;
      seen.add(domain);
      const brand = r.name.trim() || registrableDomain(domain);
      const websiteUrl = r.websiteUrl.trim() || coalesceWebsiteUrl(rawInput, domain);
      competitors.push({
        domain,
        website_url: websiteUrl,
        brand,
        summary: r.summary.trim(),
        aliases: [...r.aliases],
      });
    }
    return { competitors };
  }
  const seen = new Set<string>();
  const competitors: CompetitorItem[] = [];
  for (const r of selected) {
    const brand = r.name.trim();
    if (!brand) continue;
    const key = brand.toLowerCase();
    if (seen.has(key)) continue;
    seen.add(key);
    const rawInput = r.domain.trim();
    const domain = registrableDomain(rawInput);
    const hasDomain = domain.length >= 3;
    competitors.push({
      domain: hasDomain ? domain : "",
      website_url:
        r.websiteUrl.trim() ||
        (hasDomain ? coalesceWebsiteUrl(rawInput, domain) : ""),
      brand,
      summary: r.summary.trim(),
      aliases: [...r.aliases],
    });
  }
  return { competitors };
}

/** 手动添加竞品行时从域名推导展示名 */
export function displayNameFromDomainInput(domain: string): string {
  const host = hostnameFromWebsiteInput(domain);
  if (!host) return "";
  const base = host.split(".")[0] ?? host;
  if (!base) return host;
  return base.charAt(0).toUpperCase() + base.slice(1);
}
