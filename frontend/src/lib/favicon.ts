import { hostnameFromWebsiteInput, registrableDomain } from "@/lib/domain";

/**
 * 与后端 registrable_domain 一致：支持 URL、www、子域名、已是主域名的输入。
 * 竞品行里常见已是主域名（如 airwallex.com）；向导里可能是 www 或完整 URL。
 */
export function normalizeFaviconDomain(raw: string): string {
  const s = raw.trim();
  if (!s) return "";
  const rd = registrableDomain(s);
  if (rd && rd.includes(".")) return rd;
  return hostnameFromWebsiteInput(s);
}

/** 同源 API：后端 resolve_favicon 多源解析（静态路径 / HTML / headless）+ 磁盘缓存 */
export function faviconApiUrl(domain: string): string | null {
  const host = normalizeFaviconDomain(domain);
  if (!host) return null;
  return `/api/v1/favicon?domain=${encodeURIComponent(host)}`;
}

export function faviconCandidateUrls(domain: string): string[] {
  const api = faviconApiUrl(domain);
  return api ? [api] : [];
}
