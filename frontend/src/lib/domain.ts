const MULTIPART_SUFFIXES = new Set([
  "com.cn",
  "net.cn",
  "org.cn",
  "gov.cn",
  "edu.cn",
  "ac.cn",
  "co.uk",
  "org.uk",
  "com.au",
  "co.jp",
  "com.hk",
  "com.tw",
  "co.kr",
  "com.sg",
]);

/** 主域名（eTLD+1），与后端 registrable_domain 规则一致。 */
export function registrableDomain(raw: string): string {
  let host = hostnameFromWebsiteInput(raw);
  if (host.startsWith("www.")) host = host.slice(4);
  const parts = host.split(".");
  if (parts.length < 2) return host;
  const suffix2 = parts.slice(-2).join(".");
  if (MULTIPART_SUFFIXES.has(suffix2) && parts.length >= 3) {
    return parts.slice(-3).join(".");
  }
  return suffix2;
}

/** 从用户输入的 URL 或主机名得到小写 hostname，供 domain 类型主体写入后端。 */
export function hostnameFromWebsiteInput(raw: string): string {
  const s = raw.trim();
  if (!s) return "";
  try {
    const withProto = /^https?:\/\//i.test(s) ? s : `https://${s}`;
    return new URL(withProto).hostname.toLowerCase();
  } catch {
    return s
      .replace(/^https?:\/\//i, "")
      .split("/")[0]
      ?.trim()
      .toLowerCase() ?? "";
  }
}
