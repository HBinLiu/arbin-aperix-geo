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

/** 同源 API：后端多源解析 + 校验 */
export function faviconApiUrl(domain: string): string | null {
  const host = normalizeFaviconDomain(domain);
  if (!host) return null;
  return `/api/v1/favicon?domain=${encodeURIComponent(host)}`;
}

/** 浏览器直连回退（API 204 / 加载失败时，顺序与后端第三方源对齐） */
export function faviconFallbackUrls(domain: string): string[] {
  const host = normalizeFaviconDomain(domain);
  if (!host) return [];
  const bases =
    host.startsWith("www.") || host.split(".").length > 2
      ? [`https://${host}`]
      : [`https://${host}`, `https://www.${host}`];
  const paths = [
    "/favicon.ico",
    "/favicon.png",
    "/apple-touch-icon.png",
  ];
  const standard = bases.flatMap((b) => paths.map((p) => `${b}${p}`));
  return [
    ...standard,
    `https://favicon.yandex.net/favicon/v2/${host}?size=32`,
    `https://icons.duckduckgo.com/ip3/${host}.ico`,
    `https://icon.horse/icon/${host}`,
  ];
}

export function faviconCandidateUrls(domain: string): string[] {
  const primary = faviconApiUrl(domain);
  const fallbacks = faviconFallbackUrls(domain);
  return primary ? [primary, ...fallbacks] : fallbacks;
}
