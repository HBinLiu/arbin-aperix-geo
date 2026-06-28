import { billingCycleLabel } from "@/lib/billing/plans";
import type { BillingCycle, PayOrderListItem } from "@/types/billing";

const ORDER_TYPE_LABELS: Record<string, string> = {
  subscription: "新订阅",
  subscription_renewal: "续订",
  plan_change: "更换计划",
  usage_pack: "配额包",
};

const ORDER_STATUS_LABELS: Record<string, { label: string; variant: "success" | "warning" | "gray" | "error" }> = {
  paid: { label: "已支付", variant: "success" },
  pending: { label: "待支付", variant: "warning" },
  failed: { label: "失败", variant: "error" },
  canceled: { label: "已取消", variant: "gray" },
};

export function formatBillingDateTime(iso: string): string {
  return new Intl.DateTimeFormat("zh-CN", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(iso));
}

export function formatBillingDate(iso: string): string {
  return new Intl.DateTimeFormat("zh-CN", {
    year: "numeric",
    month: "short",
    day: "numeric",
  }).format(new Date(iso));
}

export function formatOrderAmount(cents: number): string {
  return `¥${(cents / 100).toLocaleString("zh-CN", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

export function formatSubscriptionPlanLabel(planName: string, billingCycle: BillingCycle): string {
  return `${planName} · ${billingCycleLabel(billingCycle)}`;
}

export function formatOrderType(orderType: string): string {
  return ORDER_TYPE_LABELS[orderType] ?? orderType;
}

export function formatSubjectBrand(brand: string): string {
  const trimmed = brand.trim();
  return trimmed || "—";
}

export function formatOrderPlanLabel(order: PayOrderListItem): string {
  if (order.plan_name && order.billing_cycle) {
    return formatSubscriptionPlanLabel(order.plan_name, order.billing_cycle);
  }
  if (order.product_label) {
    return order.product_label;
  }
  if (order.product_code) {
    return order.product_code;
  }
  return "—";
}

export function formatOrderStatus(status: string): { label: string; variant: "success" | "warning" | "gray" | "error" } {
  return ORDER_STATUS_LABELS[status] ?? { label: status, variant: "gray" };
}
