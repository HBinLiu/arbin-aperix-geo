import { api } from "@/api/client";
import type {
  BillingCycle,
  PaginatedPayOrders,
  PaginatedQuotaRecords,
  PayOrder,
  PayOrderPrepay,
  PayOrderSortField,
  PlanCatalog,
  PlanCode,
  QuotaRecordFilters,
  QuotaRecordFiltersApi,
  QuotaRecordFiltersMeta,
  QuotaRecordSortField,
  TenantSubscription,
  UsagePackCatalog,
  UsagePackCode,
} from "@/types/billing";
import { buildQuotaRecordFiltersMeta } from "@/lib/billing/quota-records";

export async function fetchTenantSubscription(): Promise<TenantSubscription> {
  const { data } = await api.get<TenantSubscription>("/billing/subscription");
  return data;
}

export async function fetchPlanCatalog(): Promise<PlanCatalog> {
  const { data } = await api.get<PlanCatalog>("/billing/plans");
  return data;
}

export async function fetchUsagePackCatalog(): Promise<UsagePackCatalog> {
  const { data } = await api.get<UsagePackCatalog>("/billing/usage-packs");
  return data;
}

export async function fetchPayOrders(params: {
  page: number;
  page_size: number;
  sort_by: PayOrderSortField;
  order: "asc" | "desc";
}): Promise<PaginatedPayOrders> {
  const { data } = await api.post<PaginatedPayOrders>("/billing/orders", params);
  return data;
}

export async function fetchQuotaRecordFilters(): Promise<QuotaRecordFiltersMeta> {
  const { data } = await api.get<QuotaRecordFiltersApi>("/billing/quota-records/filters");
  return buildQuotaRecordFiltersMeta(data);
}

export async function fetchQuotaRecords(
  params: {
    page: number;
    page_size: number;
    sort_by: QuotaRecordSortField;
    order: "asc" | "desc";
  } & QuotaRecordFilters,
): Promise<PaginatedQuotaRecords> {
  const { data } = await api.post<PaginatedQuotaRecords>("/billing/quota-records", params);
  return data;
}

export async function exportQuotaRecords(
  params: {
    sort_by: QuotaRecordSortField;
    order: "asc" | "desc";
  } & QuotaRecordFilters,
): Promise<Blob> {
  const { data } = await api.post<Blob>("/billing/quota-records/export", params, {
    responseType: "blob",
  });
  return data;
}

export async function createSubscriptionOrder(input: {
  plan_code: PlanCode;
  billing_cycle: BillingCycle;
}): Promise<PayOrder> {
  const { data } = await api.post<PayOrder>("/billing/orders/subscription", input, {
    skipErrorToast: true,
  });
  return data;
}

export async function createUsagePackOrder(input: {
  product_code: UsagePackCode;
  quantity?: number;
}): Promise<PayOrder> {
  const { data } = await api.post<PayOrder>("/billing/orders/usage-pack", input, {
    skipErrorToast: true,
  });
  return data;
}

export async function cancelPayOrder(orderId: string): Promise<PayOrder> {
  const { data } = await api.post<PayOrder>(`/billing/orders/${orderId}/cancel`, undefined, {
    skipErrorToast: true,
  });
  return data;
}

export async function fetchPayOrder(orderId: string): Promise<PayOrder> {
  const { data } = await api.get<PayOrder>(`/billing/orders/${orderId}`);
  return data;
}

export async function prepayPayOrder(orderId: string): Promise<PayOrderPrepay> {
  const { data } = await api.post<PayOrderPrepay>(`/billing/orders/${orderId}/pay`, undefined, {
    skipErrorToast: true,
  });
  return data;
}

export async function simulatePayOrder(orderId: string): Promise<PayOrder> {
  const { data } = await api.post<PayOrder>(`/billing/orders/${orderId}/simulate-pay`, undefined, {
    skipErrorToast: true,
  });
  return data;
}
