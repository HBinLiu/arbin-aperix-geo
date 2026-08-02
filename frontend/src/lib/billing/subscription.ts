import type { TenantSubscription } from "@/types/billing";

/** 订阅是否仍在有效期内（与后端 subscription_active 对齐）。 */
export function isSubscriptionActive(subscription?: TenantSubscription | null): boolean {
  return Boolean(subscription?.subscription_active);
}

/** 订阅已到期或不可用。 */
export function isSubscriptionExpired(subscription?: TenantSubscription | null): boolean {
  if (!subscription) return false;
  if (!subscription.subscription_active) return true;
  return subscription.status === "expired";
}

export function subscriptionStatusLabel(subscription: TenantSubscription): string {
  if (isSubscriptionExpired(subscription)) return "已到期";
  if (subscription.status === "canceled") return "已取消（周期内仍有效）";
  if (subscription.status === "active") return "生效中";
  return subscription.status;
}
