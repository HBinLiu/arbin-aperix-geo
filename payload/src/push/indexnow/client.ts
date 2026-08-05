/** IndexNow · 主动通知 Bing 等参与搜索引擎 */

import { getWebsiteUrl } from "../../lib/urls";

export type IndexNowPushResult = {
  ok: boolean;
  status: number;
  message?: string;
  raw?: string;
};

const INDEXNOW_API_HOST = "api.indexnow.org";
const INDEXNOW_PATH = "/indexnow";
/** 协议上限 10000；单批稍保守便于日志 */
export const INDEXNOW_BATCH_SIZE = 5000;

function trimEnv(name: string): string {
  return (process.env[name] || "").trim();
}

export function getIndexNowKey(): string {
  return trimEnv("INDEXNOW_KEY");
}

/** 未配置 INDEXNOW_KEY 时关闭 */
export function isIndexNowPushEnabled(): boolean {
  return Boolean(getIndexNowKey());
}

/** 官网 host（无协议），如 www.aperix.cn */
export function getIndexNowHost(): string | null {
  const override = trimEnv("INDEXNOW_HOST");
  if (override) return override.replace(/^https?:\/\//i, "").replace(/\/$/, "");
  const base = getWebsiteUrl();
  if (!/^https:\/\//i.test(base)) return null;
  try {
    return new URL(base).host;
  } catch {
    return null;
  }
}

export function getIndexNowKeyLocation(key = getIndexNowKey()): string | null {
  const host = getIndexNowHost();
  if (!host || !key) return null;
  return `https://${host}/${key}.txt`;
}

/**
 * 向 IndexNow 推送 URL 列表。
 * 成功：HTTP 200 / 202；失败不抛错，返回结构化结果。
 */
export async function pushUrlsToIndexNow(urls: string[]): Promise<IndexNowPushResult> {
  const key = getIndexNowKey();
  const host = getIndexNowHost();
  if (!key || !host) {
    return {
      ok: false,
      status: 0,
      message: "INDEXNOW_KEY 未配置，或 PUBLIC_WEBSITE_URL / INDEXNOW_HOST 无效",
    };
  }

  const unique = [
    ...new Set(
      urls
        .map((url) => url.trim())
        .filter((url) => {
          if (!/^https:\/\//i.test(url)) return false;
          try {
            return new URL(url).host === host;
          } catch {
            return false;
          }
        }),
    ),
  ];
  if (unique.length === 0) {
    return { ok: false, status: 0, message: "没有可推送的同站 https URL" };
  }

  const keyLocation = getIndexNowKeyLocation(key);
  const body = JSON.stringify({
    host,
    key,
    ...(keyLocation ? { keyLocation } : {}),
    urlList: unique,
  });

  try {
    const res = await fetch(`https://${INDEXNOW_API_HOST}${INDEXNOW_PATH}`, {
      method: "POST",
      headers: { "Content-Type": "application/json; charset=utf-8" },
      body,
      signal: AbortSignal.timeout(30_000),
    });
    const raw = await res.text();
    const ok = res.status === 200 || res.status === 202;
    return {
      ok,
      status: res.status,
      message: ok
        ? res.status === 202
          ? "Accepted（key 校验待完成，确认 {key}.txt 已部署）"
          : undefined
        : raw.slice(0, 200) || `HTTP ${res.status}`,
      raw: raw || undefined,
    };
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    return { ok: false, status: 0, message };
  }
}
