import { pushUrlsToBaidu, type BaiduPushResult } from "./client";

const BATCH_SIZE = 2000;

export type BaiduSitemapPushSummary = {
  collected: number;
  batches: number;
  results: BaiduPushResult[];
  ok: boolean;
};

/** 按百度单次上限分批推送 */
export async function pushUrlListToBaidu(urls: string[]): Promise<BaiduSitemapPushSummary> {
  const unique = [...new Set(urls.map((u) => u.trim()).filter(Boolean))];
  const results: BaiduPushResult[] = [];
  let batches = 0;

  for (let i = 0; i < unique.length; i += BATCH_SIZE) {
    batches += 1;
    const chunk = unique.slice(i, i + BATCH_SIZE);
    results.push(await pushUrlsToBaidu(chunk));
  }

  return {
    collected: unique.length,
    batches,
    results,
    ok: results.length > 0 && results.every((r) => r.ok),
  };
}
