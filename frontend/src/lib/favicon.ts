import { hostnameFromWebsiteInput, registrableDomain } from "@/lib/domain";

/**
 * 与后端 normalize_favicon_domain 一致：支持 URL、裸域 example.com、www、子域名。
 * 裸主域归一为 eTLD+1（如 wise.com）；多级子域保留完整主机名。
 */
export function normalizeFaviconDomain(raw: string): string {
  const s = raw.trim();
  if (!s) return "";

  let host = hostnameFromWebsiteInput(s);
  if (!host && /^[^\s/]+$/i.test(s)) {
    host = s.replace(/^https?:\/\//i, "").split("/")[0]?.split(":")[0]?.trim().toLowerCase() ?? "";
  }
  if (host.startsWith("www.")) {
    host = host.slice(4);
  }
  if (!host) return "";

  const root = registrableDomain(host);
  if (root && host !== root && host.endsWith(`.${root}`)) {
    return host;
  }
  return root || host;
}

export type FaviconClientStatus = "ok" | "miss";

const faviconClientCache = new Map<string, FaviconClientStatus>();

export function faviconCacheKey(domain: string, pageUrl?: string | null): string {
  const host = normalizeFaviconDomain(domain);
  if (!host) return "";
  const page = pageUrl?.trim();
  return page ? `${host}\0${page}` : host;
}

/** 会话内 favicon 状态，避免同页重复请求已知 miss。 */
export function getFaviconClientStatus(
  domain: string,
  pageUrl?: string | null,
): FaviconClientStatus | undefined {
  const key = faviconCacheKey(domain, pageUrl);
  if (!key) return undefined;
  return faviconClientCache.get(key);
}

export function markFaviconClientOk(domain: string, pageUrl?: string | null): void {
  const key = faviconCacheKey(domain, pageUrl);
  if (key) faviconClientCache.set(key, "ok");
}

export function markFaviconClientMiss(domain: string, pageUrl?: string | null): void {
  const key = faviconCacheKey(domain, pageUrl);
  if (key) faviconClientCache.set(key, "miss");
}

/** 同源 API：后端 resolve_favicon + 磁盘缓存；未命中返回 204 */
export function faviconApiUrl(domain: string, pageUrl?: string | null): string | null {
  const host = normalizeFaviconDomain(domain);
  if (!host) return null;
  const params = new URLSearchParams({ domain: host });
  const page = pageUrl?.trim();
  if (page) params.set("page_url", page);
  return `/api/v1/favicon?${params.toString()}`;
}

export function faviconCandidateUrls(domain: string, pageUrl?: string | null): string[] {
  if (getFaviconClientStatus(domain, pageUrl) === "miss") return [];
  const api = faviconApiUrl(domain, pageUrl);
  return api ? [api] : [];
}
