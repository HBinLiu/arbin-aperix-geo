import { hostnameFromWebsiteInput, registrableDomain } from "@/lib/domain";
import type { CompetitorRow, DiscoveredCompetitor, SubjectMode } from "@/types";

export const MAX_SETUP_COMPETITORS = 5;

export function newCompetitorRow(partial?: Partial<CompetitorRow>): CompetitorRow {
  return {
    id: crypto.randomUUID(),
    name: "",
    domain: "",
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

export function rowsFromDiscover(
  mode: SubjectMode,
  competitors: DiscoveredCompetitor[],
  brandNames: string[],
): CompetitorRow[] {
  if (mode === "domain") {
    return competitors.slice(0, MAX_SETUP_COMPETITORS).map((c) =>
      newCompetitorRow({
        name: c.site_name.trim(),
        domain: registrableDomain(c.domain),
        selected: true,
      }),
    );
  }
  return brandNames.slice(0, MAX_SETUP_COMPETITORS).map((name) =>
    newCompetitorRow({ name: name.trim(), domain: "", selected: true }),
  );
}

export function rowsToPersist(
  mode: SubjectMode,
  rows: CompetitorRow[],
): { competitors: { domain: string; site_name: string }[]; brand_names: string[] } {
  const selected = rows.filter((r) => r.selected);
  if (mode === "domain") {
    const seen = new Set<string>();
    const competitors: { domain: string; site_name: string }[] = [];
    for (const r of selected) {
      const domain = registrableDomain(r.domain || r.name);
      if (domain.length < 3 || seen.has(domain)) continue;
      seen.add(domain);
      const site_name = r.name.trim() || domainToDisplayName(domain);
      competitors.push({ domain, site_name });
    }
    return { competitors, brand_names: [] };
  }
  const brand_names = selected.map((r) => r.name.trim()).filter(Boolean);
  return { competitors: [], brand_names: [...new Set(brand_names)] };
}
