import { hostnameFromWebsiteInput, registrableDomain } from "@/lib/domain";
import type { CompetitorItem, CompetitorRow, DiscoveredCompetitor, SubjectMode } from "@/types";

export const MAX_SETUP_COMPETITORS = 5;

export function newCompetitorRow(partial?: Partial<CompetitorRow>): CompetitorRow {
  return {
    id: crypto.randomUUID(),
    name: "",
    domain: "",
    summary: "",
    selected: true,
    ...partial,
  };
}

/** 从域名推导展示用品牌名（如 airwallex.com → Airwallex） */
export function domainToDisplayName(domain: string): string {
  const host = hostnameFromWebsiteInput(domain);
  if (!host) return "";
  const base = host.split(".")[0] ?? host;
  if (!base) return host;
  return base.charAt(0).toUpperCase() + base.slice(1);
}

export function rowsFromDiscover(competitors: DiscoveredCompetitor[]): CompetitorRow[] {
  return competitors.slice(0, MAX_SETUP_COMPETITORS).map((c) =>
    newCompetitorRow({
      name: c.brand.trim() || (c.domain ? registrableDomain(c.domain) : ""),
      domain: c.domain ? registrableDomain(c.domain) : "",
      summary: (c.summary ?? "").trim(),
      selected: true,
    }),
  );
}

export function rowsToPersist(mode: SubjectMode, rows: CompetitorRow[]): { competitors: CompetitorItem[] } {
  const selected = rows.filter((r) => r.selected);
  if (mode === "domain") {
    const seen = new Set<string>();
    const competitors: CompetitorItem[] = [];
    for (const r of selected) {
      const domain = registrableDomain(r.domain || r.name);
      if (domain.length < 3 || seen.has(domain)) continue;
      seen.add(domain);
      const brand = r.name.trim() || registrableDomain(domain);
      competitors.push({ domain, website_url: "", brand, summary: r.summary.trim() });
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
    competitors.push({ domain: "", website_url: "", brand, summary: r.summary.trim() });
  }
  return { competitors };
}
