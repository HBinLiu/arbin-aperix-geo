import {
  INDEXNOW_BATCH_SIZE,
  pushUrlsToIndexNow,
  type IndexNowPushResult,
} from "./client";

export type IndexNowSitemapPushSummary = {
  collected: number;
  batches: number;
  results: IndexNowPushResult[];
  ok: boolean;
};

/** 按 IndexNow 单次上限分批推送 */
export async function pushUrlListToIndexNow(
  urls: string[],
): Promise<IndexNowSitemapPushSummary> {
  const unique = [...new Set(urls.map((u) => u.trim()).filter(Boolean))];
  const results: IndexNowPushResult[] = [];
  let batches = 0;

  for (let i = 0; i < unique.length; i += INDEXNOW_BATCH_SIZE) {
    batches += 1;
    const chunk = unique.slice(i, i + INDEXNOW_BATCH_SIZE);
    results.push(await pushUrlsToIndexNow(chunk));
  }

  return {
    collected: unique.length,
    batches,
    results,
    ok: results.length > 0 && results.every((r) => r.ok),
  };
}
