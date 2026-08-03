/** 百度搜索资源平台 · 普通收录 API 推送 */

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

export function getBaiduPushEndpoint(): string | null {
  const site = trimEnv("BAIDU_PUSH_SITE");
  const token = trimEnv("BAIDU_PUSH_TOKEN");
  if (!site || !token) return null;

  // site 必须是已验证站点主机名，勿带 https://
  const host = site.replace(/^https?:\/\//i, "").replace(/\/$/, "");
  const params = new URLSearchParams({ site: host, token });
  return `http://data.zz.baidu.com/urls?${params}`;
}

/**
 * 向百度普通收录 API 推送 URL（每行一个）。
 * 单次建议 ≤ 2000 条；失败不抛错，返回结构化结果便于日志。
 */
export async function pushUrlsToBaidu(urls: string[]): Promise<BaiduPushResult> {
  const endpoint = getBaiduPushEndpoint();
  if (!endpoint) {
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

  try {
    const res = await fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "text/plain" },
      body: unique.join("\n"),
      signal: AbortSignal.timeout(15_000),
    });
    const raw = await res.text();
    let parsed: Record<string, unknown> = {};
    try {
      parsed = JSON.parse(raw) as Record<string, unknown>;
    } catch {
      /* 非 JSON */
    }

    if (!res.ok || parsed.error != null) {
      return {
        ok: false,
        status: res.status,
        error: parsed.error as number | string | undefined,
        message: typeof parsed.message === "string" ? parsed.message : raw.slice(0, 200),
        raw,
      };
    }

    return {
      ok: true,
      status: res.status,
      success: typeof parsed.success === "number" ? parsed.success : undefined,
      remain: typeof parsed.remain === "number" ? parsed.remain : undefined,
      not_same_site: Array.isArray(parsed.not_same_site)
        ? (parsed.not_same_site as string[])
        : undefined,
      not_valid: Array.isArray(parsed.not_valid) ? (parsed.not_valid as string[]) : undefined,
      raw,
    };
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    return { ok: false, status: 0, message };
  }
}
