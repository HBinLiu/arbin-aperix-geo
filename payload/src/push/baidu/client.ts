/** 百度搜索资源平台 · 普通收录 API 推送 */

import http from "node:http";

export type BaiduPushResult = {
  ok: boolean;
  status: number;
  success?: number;
  remain?: number;
  not_same_site?: string[];
  not_valid?: string[];
  error?: number | string;
  message?: string;
  raw?: string;
};

function trimEnv(name: string): string {
  return (process.env[name] || "").trim();
}

/** 未配置 token 时视为关闭推送 */
export function isBaiduPushEnabled(): boolean {
  return Boolean(trimEnv("BAIDU_PUSH_TOKEN") && trimEnv("BAIDU_PUSH_SITE"));
}

/**
 * 与站长后台 curl 完全一致的 path（勿用 URL / fetch，会把 https:// 编成 %3A%2F%2F）。
 */
export function getBaiduPushRequestPath(siteOverride?: string): string | null {
  const site = (siteOverride ?? trimEnv("BAIDU_PUSH_SITE")).replace(/\/$/, "");
  const token = trimEnv("BAIDU_PUSH_TOKEN");
  if (!site || !token) return null;
  return `/urls?site=${site}&token=${token}`;
}

/** @deprecated 仅调试；真实请求请用 getBaiduPushRequestPath + http.request */
export function getBaiduPushEndpoint(siteOverride?: string): string | null {
  const path = getBaiduPushRequestPath(siteOverride);
  if (!path) return null;
  return `http://data.zz.baidu.com${path}`;
}

function siteCandidates(): string[] {
  const raw = trimEnv("BAIDU_PUSH_SITE").replace(/\/$/, "");
  if (!raw) return [];
  const host = raw.replace(/^https?:\/\//i, "");
  const withHttps = host.startsWith("http") ? host : `https://${host}`;
  return [...new Set([raw, withHttps, host].filter(Boolean))];
}

function postBaiduUrls(path: string, body: string): Promise<{ status: number; raw: string }> {
  return new Promise((resolve, reject) => {
    const req = http.request(
      {
        hostname: "data.zz.baidu.com",
        port: 80,
        path,
        method: "POST",
        headers: {
          "Content-Type": "text/plain",
          "Content-Length": Buffer.byteLength(body, "utf8"),
          "User-Agent": "curl/7.12.1",
        },
      },
      (res) => {
        const chunks: Buffer[] = [];
        res.on("data", (chunk: Buffer) => chunks.push(chunk));
        res.on("end", () => {
          resolve({
            status: res.statusCode ?? 0,
            raw: Buffer.concat(chunks).toString("utf8"),
          });
        });
      },
    );
    req.setTimeout(15_000, () => {
      req.destroy(new Error("百度推送超时"));
    });
    req.on("error", reject);
    req.write(body, "utf8");
    req.end();
  });
}

function parseBaiduResult(status: number, raw: string): BaiduPushResult {
  let parsed: Record<string, unknown> = {};
  try {
    parsed = JSON.parse(raw) as Record<string, unknown>;
  } catch {
    /* 非 JSON */
  }

  if (status < 200 || status >= 300 || parsed.error != null) {
    return {
      ok: false,
      status,
      error: parsed.error as number | string | undefined,
      message: typeof parsed.message === "string" ? parsed.message : raw.slice(0, 200),
      raw,
    };
  }

  return {
    ok: true,
    status,
    success: typeof parsed.success === "number" ? parsed.success : undefined,
    remain: typeof parsed.remain === "number" ? parsed.remain : undefined,
    not_same_site: Array.isArray(parsed.not_same_site)
      ? (parsed.not_same_site as string[])
      : undefined,
    not_valid: Array.isArray(parsed.not_valid) ? (parsed.not_valid as string[]) : undefined,
    raw,
  };
}

/**
 * 向百度普通收录 API 推送 URL（每行一个）。
 * 单次建议 ≤ 2000 条；失败不抛错，返回结构化结果便于日志。
 */
export async function pushUrlsToBaidu(urls: string[]): Promise<BaiduPushResult> {
  const candidates = siteCandidates();
  if (candidates.length === 0 || !trimEnv("BAIDU_PUSH_TOKEN")) {
    return { ok: false, status: 0, message: "BAIDU_PUSH_SITE / BAIDU_PUSH_TOKEN 未配置" };
  }

  const unique = [
    ...new Set(
      urls
        .map((url) => url.trim())
        .filter((url) => /^https?:\/\//i.test(url)),
    ),
  ];
  if (unique.length === 0) {
    return { ok: false, status: 0, message: "没有可推送的 URL" };
  }

  const body = unique.join("\n");
  let last: BaiduPushResult = { ok: false, status: 0, message: "未尝试推送" };

  for (const site of candidates) {
    const path = getBaiduPushRequestPath(site);
    if (!path) continue;

    try {
      const { status, raw } = await postBaiduUrls(path, body);
      last = parseBaiduResult(status, raw);
      if (last.ok) return last;
      if (String(last.message || "").includes("site init fail")) {
        continue;
      }
      return last;
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      last = { ok: false, status: 0, message };
      return last;
    }
  }

  if (String(last.message || "").includes("site init fail")) {
    last.message =
      "site init fail（已分别尝试带/不带 https://）。请确认站长平台该站点已验证，且 BAIDU_PUSH_SITE/TOKEN 与后台 API 示例完全一致。";
  }
  return last;
}
