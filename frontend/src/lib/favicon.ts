import {
  coalesceWebsiteUrl,
  externalHref,
  faviconDomainKey,
  registrableDomain,
} from "@/lib/domain";

export type FaviconInput = {
  host: string;
  pageUrl: string;
};

/** 将用户输入或站点 URL 解析为 favicon 请求参数（后端按 domain 缓存，按 url 抓取）。 */
export function resolveFaviconInput(raw: string): FaviconInput | null {
  const trimmed = raw.trim();
  if (!trimmed) return null;
  const domain = registrableDomain(trimmed);
  const pageUrl = coalesceWebsiteUrl(trimmed, domain);
  if (!pageUrl) return null;

  const host = faviconDomainKey(pageUrl);
  if (!host || !host.includes(".")) return null;
  return { host, pageUrl };
}

/** 仅有 host/domain 时构造页面 URL（裸 host 补 http://）。 */
export function faviconUrlFromHost(host: string): string {
  return externalHref(host.trim());
}

export type FaviconClientStatus = "ok" | "miss";

const faviconClientCache = new Map<string, FaviconClientStatus>();

export function faviconCacheKey(url: string): string {
  return resolveFaviconInput(url)?.pageUrl ?? "";
}

/** 会话内 favicon 状态，避免同页重复请求已知 miss。 */
export function getFaviconClientStatus(url: string): FaviconClientStatus | undefined {
  const key = faviconCacheKey(url);
  if (!key) return undefined;
  return faviconClientCache.get(key);
}

export function markFaviconClientOk(url: string): void {
  const key = faviconCacheKey(url);
  if (key) faviconClientCache.set(key, "ok");
}

export function markFaviconClientMiss(url: string): void {
  const key = faviconCacheKey(url);
  if (key) faviconClientCache.set(key, "miss");
}

/** 同源 API：后端 resolve_favicon + 磁盘缓存；未命中返回 204 */
export function faviconApiUrl(url: string): string | null {
  const resolved = resolveFaviconInput(url);
  if (!resolved) return null;
  const params = new URLSearchParams({ url: resolved.pageUrl });
  return `/api/v1/favicon?${params.toString()}`;
}

export function faviconCandidateUrls(url: string): string[] {
  if (getFaviconClientStatus(url) === "miss") return [];
  const api = faviconApiUrl(url);
  return api ? [api] : [];
}

/** 竞品/主体等：优先 website URL，否则由主域名构造首页 URL。 */
export function faviconUrlFromWebsite(
  websiteUrl: string | null | undefined,
  domain: string | null | undefined,
): string | null {
  const url = websiteUrl?.trim();
  if (url) return coalesceWebsiteUrl(url, domain?.trim() || registrableDomain(url));
  const host = domain?.trim();
  if (!host) return null;
  return faviconUrlFromHost(host);
}

/** 域名输入框 blur 后解析 favicon URL（Setup 竞品、添加/编辑竞品弹窗）。 */
export function faviconUrlFromDomainInput(
  raw: string,
  websiteUrl?: string | null,
): string | null {
  const source = raw.trim();
  if (!source) return null;
  const domain = registrableDomain(source);
  if (!domain) return null;
  const pageUrl = coalesceWebsiteUrl(websiteUrl?.trim() || source, domain);
  return faviconUrlFromWebsite(pageUrl, domain);
}
