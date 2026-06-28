import type { TenantSubscription } from "@/types/billing";

export type QuotaWarningCode = "20pct" | "5pct" | "0pct";

const THRESHOLDS: { code: QuotaWarningCode; ratio: number }[] = [
  { code: "20pct", ratio: 0.2 },
  { code: "5pct", ratio: 0.05 },
  { code: "0pct", ratio: 0 },
];

export function computeQuotaWarning(subscription: TenantSubscription): QuotaWarningCode | null {
  const { usage } = subscription;
  const total = Math.max(usage.monthly_limit, 0) + Math.max(usage.usage_pack_balance, 0);
  if (total <= 0) return null;
  const ratio = Math.max(usage.ai_requests_available, 0) / total;

  let matched: QuotaWarningCode | null = null;
  for (const row of THRESHOLDS) {
    if (ratio <= row.ratio) matched = row.code;
  }
  return matched;
}

export function quotaWarningStorageKey(subscription: TenantSubscription, code: QuotaWarningCode): string {
  const anchor = subscription.ai_period_start ?? subscription.current_period_start;
  return `aperix:quota-warn:${subscription.tenant_id}:${anchor}:${code}`;
}

export function quotaWarningMessage(code: QuotaWarningCode, available: number): string {
  if (code === "0pct") {
    return "AI 请求额度已用尽，请升级订阅或购买配额包。";
  }
  if (code === "5pct") {
    return `AI 请求额度即将用尽（剩余 ${available.toLocaleString("zh-CN")} 次）。`;
  }
  return `AI 请求额度剩余不足 20%（可用 ${available.toLocaleString("zh-CN")} 次）。`;
}
