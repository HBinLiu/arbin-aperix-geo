/** Subscription billing API types (aligned with backend schemas). */

export type BillingCycle = "monthly" | "quarterly" | "yearly";

export type PlanCode = "personal" | "premium" | "ultimate" | "enterprise";

export type UsagePackCode = "pack_1000" | "pack_5000" | "pack_10000" | "custom";

export type PlanLimitItem = {
  key: string;
  label: string;
  description: string;
  value: string;
};

export type PlanPriceItem = {
  billing_cycle: BillingCycle;
  monthly_cents: number | null;
  period_total_cents: number | null;
  discount_badge: string | null;
};

export type PlanCatalogItem = {
  code: PlanCode;
  name: string;
  description: string;
  orderable: boolean;
  limits: PlanLimitItem[];
  prices: PlanPriceItem[];
};

export type BillingCycleOption = {
  id: BillingCycle;
  label: string;
  badge: string | null;
};

export type PlanCatalog = {
  plans: PlanCatalogItem[];
  billing_cycles: BillingCycleOption[];
};

export type UsagePackCatalogItem = {
  code: string;
  title: string;
  order_label: string;
  quantity: number;
  price_cents: number;
  unit_price_cents: number;
};

export type UsagePackCatalog = {
  packs: UsagePackCatalogItem[];
};

export type PlanLimits = {
  max_subjects: number;
  max_per_platforms: number;
  max_per_competitors: number;
  max_prompts_total: number;
  per_month_usages: number;
  sampling_frequency: string;
};

export type TenantUsage = {
  subjects_count: number;
  prompts_count: number;
  monthly_limit: number;
  monthly_used: number;
  monthly_remaining: number;
  usage_pack_balance: number;
  ai_requests_available: number;
};

export type TenantSubscription = {
  tenant_id: string;
  plan_code: PlanCode;
  plan_name: string;
  billing_cycle: BillingCycle;
  status: string;
  current_period_start: string;
  current_period_end: string;
  ai_period_start: string | null;
  ai_period_end: string | null;
  subscription_active: boolean;
  limits: PlanLimits;
  usage: TenantUsage;
};

export type PayOrder = {
  id: string;
  order_type: string;
  amount_cents: number;
  status: string;
  plan_code?: PlanCode | null;
  billing_cycle?: BillingCycle | null;
  product_code?: string | null;
  product_label?: string | null;
  quantity?: number | null;
};

export type PayOrderListItem = PayOrder & {
  created_at: string;
  paid_at?: string | null;
  plan_name?: string | null;
};

export type PaginatedPayOrders = {
  items: PayOrderListItem[];
  total: number;
  page: number;
  page_size: number;
};

export type QuotaRecordListItem = {
  id: string;
  created_at: string;
  record_type: QuotaRecordType;
  record_type_label: string;
  source: string;
  source_label: string;
  amount_delta: number;
  subject_id: string;
  subject_brand: string;
};

export type PaginatedQuotaRecords = {
  items: QuotaRecordListItem[];
  total: number;
  page: number;
  page_size: number;
};

export type PayOrderSortField = "created_at" | "amount_cents" | "status";

export type QuotaRecordSortField = "created_at" | "source" | "amount_delta";

export type QuotaRecordType =
  | "subscription_consume"
  | "pack_quota_consume"
  | "usage_pack_purchase"
  | "subscription_grant";

export type QuotaRecordDays = 1 | 7 | 30 | 90;

export type QuotaRecordTypeFilter = "all" | QuotaRecordType;

export type QuotaRecordFilters = {
  days: QuotaRecordDays;
  record_type: QuotaRecordTypeFilter;
};

export type QuotaRecordDayFilterOption = {
  value: QuotaRecordDays;
  label: string;
};

export type QuotaRecordTypeFilterOption = {
  value: QuotaRecordType;
  label: string;
};

export type QuotaRecordTypeFilterUiOption = {
  value: QuotaRecordTypeFilter;
  label: string;
};

export type QuotaRecordFiltersApi = {
  days: QuotaRecordDays[];
  record_types: QuotaRecordTypeFilterOption[];
  default_days: QuotaRecordDays;
};

export type QuotaRecordFiltersMeta = {
  days: QuotaRecordDayFilterOption[];
  record_types: QuotaRecordTypeFilterUiOption[];
  default_days: QuotaRecordDays;
  default_record_type: QuotaRecordTypeFilter;
};
