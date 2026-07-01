import { getDomain } from "tldts";

/**
 * URL / domain 语义（与后端 utils/net + schemas/url_fields 对齐）：
 *
 * - `domain`（主体/竞品字段）→ eTLD+1，用 `registrableDomain`
 * - `website_url`（存储）→ 用户输入；有 scheme 则保留；裸 host/path 不补 scheme
 * - 抓取 / favicon API → 后端 `parse_url` 补 scheme（裸域默认 http://）
 * - 可点击外链 → `externalHref`（裸 host 补 http://）
 */

/** 主域名（eTLD+1），与后端 registrable_from (publicsuffix2) 对齐。 */
export function registrableDomain(raw: string): string {
  const host = hostnameFromWebsiteInput(raw);
  if (!host) return "";
  return getDomain(host, { detectIp: false, allowPrivateDomains: false }) ?? "";
}

/** 从用户输入的 URL 或主机名得到小写 hostname，供 domain 类型主体写入后端。 */
export function hostnameFromWebsiteInput(raw: string): string {
  const s = raw.trim();
  if (!s) return "";
  try {
    const withProto = /^https?:\/\//i.test(s) ? s : `https://${s}`;
    return new URL(withProto).hostname.toLowerCase().replace(/^www\./, "");
  } catch {
    return s
      .replace(/^https?:\/\//i, "")
      .split("/")[0]
      ?.replace(/^www\./, "")
      ?.trim()
      .toLowerCase() ?? "";
  }
}

/**
 * Favicon 缓存键：裸主域归 eTLD+1；gov 等有意义子域保留完整主机名。
 * 与后端 favicon_from 一致。
 */
export function faviconDomainKey(raw: string): string {
  const host = hostnameFromWebsiteInput(raw);
  if (!host) return "";
  const root = registrableDomain(host);
  if (root && host !== root && host.endsWith(`.${root}`)) {
    return host;
  }
  return root || host;
}

/** 将用户输入规范为存储用 website_url（保留 http(s)；裸域名/路径不强制加 https）。 */
export function websiteUrlFromInput(raw: string): string {
  const s = raw.trim();
  if (!s) return "";
  if (/^https?:\/\//i.test(s)) return s;
  return s.replace(/^\/+/, "");
}

/**
 * 可点击外链：保留 http(s)；裸 host/path 用 http://（不强制 https）。
 * 无 scheme 的 href 会被浏览器当作相对路径，故裸域名需补可访问协议。
 */
export function externalHref(raw: string): string {
  const s = raw.trim();
  if (!s) return "";
  if (/^https?:\/\//i.test(s)) return s;
  return `http://${s.replace(/^\/+/, "")}`;
}
