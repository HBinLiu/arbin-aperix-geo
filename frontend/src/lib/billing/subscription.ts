import type { TenantSubscription } from "@/types/billing";

function periodEndMs(subscription: TenantSubscription): number {
  return Date.parse(subscription.current_period_end);
}

/** 订阅是否仍在有效期内（结合后端标志与本地 period_end，避免缓存滞后）。 */
export function isSubscriptionActive(
  subscription?: TenantSubscription | null,
  nowMs: number = Date.now(),
): boolean {
  if (!subscription?.subscription_active) return false;
  if (subscription.status === "expired") return false;
  const end = periodEndMs(subscription);
  if (Number.isFinite(end) && nowMs >= end) return false;
  return true;
}

/** 订阅已到期或不可用。 */
export function isSubscriptionExpired(
  subscription?: TenantSubscription | null,
  nowMs: number = Date.now(),
): boolean {
  if (!subscription) return false;
  return !isSubscriptionActive(subscription, nowMs);
}

/** 距 period_end 的毫秒数；已过期或无法解析时返回 null。 */
export function msUntilSubscriptionPeriodEnd(
  subscription?: TenantSubscription | null,
  nowMs: number = Date.now(),
): number | null {
  if (!subscription) return null;
  const end = periodEndMs(subscription);
  if (!Number.isFinite(end)) return null;
  const remaining = end - nowMs;
  return remaining > 0 ? remaining : null;
}
