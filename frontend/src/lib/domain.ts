import { getDomain } from "tldts";

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

/** 将用户输入的 URL / 域名规范为可访问地址（保留路径；最终校验由后端 HttpUrl 完成）。 */
export function websiteUrlFromInput(raw: string): string {
  const s = raw.trim();
  if (!s) return "";
  if (/^https?:\/\//i.test(s)) return s;
  if (s.includes("/")) return `https://${s.replace(/^\/\//, "")}`;
  const host = hostnameFromWebsiteInput(s);
  if (!host) return "";
  return `https://${host}/`;
}
