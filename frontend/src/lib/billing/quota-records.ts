import type { SemanticBadgeVariant } from "@/components/ui/badge";
import type {
  QuotaRecordDays,
  QuotaRecordFiltersApi,
  QuotaRecordFiltersMeta,
  QuotaRecordType,
  QuotaRecordTypeFilter,
  QuotaRecordTypeFilterUiOption,
} from "@/types/billing";

export const ALL_QUOTA_RECORD_TYPE = "all" satisfies QuotaRecordTypeFilter;
export const ALL_QUOTA_RECORD_TYPE_LABEL = "全部类型";

export const DEFAULT_QUOTA_RECORD_DAYS = 30 satisfies QuotaRecordDays;
export const DEFAULT_QUOTA_RECORD_TYPE = ALL_QUOTA_RECORD_TYPE;

const QUOTA_RECORD_TYPE_BADGE_VARIANTS: Record<QuotaRecordType, SemanticBadgeVariant> = {
  subscription_consume: "primary",
  pack_quota_consume: "warning",
  usage_pack_purchase: "success",
  subscription_grant: "info",
};

export function quotaRecordTypeBadgeVariant(recordType: QuotaRecordType): SemanticBadgeVariant {
  return QUOTA_RECORD_TYPE_BADGE_VARIANTS[recordType] ?? "gray";
}

export function formatQuotaAmountDelta(delta: number): string {
  return delta > 0 ? `+${delta}` : String(delta);
}

export function formatQuotaRecordDayLabel(days: number): string {
  return `${days}天`;
}

export const ALLOWED_QUOTA_RECORD_DAYS = [1, 7, 30, 90] as const satisfies readonly QuotaRecordDays[];

export function fallbackQuotaRecordFiltersMeta(): QuotaRecordFiltersMeta {
  return {
    days: ALLOWED_QUOTA_RECORD_DAYS.map((value) => ({
      value,
      label: formatQuotaRecordDayLabel(value),
    })),
    record_types: [{ value: ALL_QUOTA_RECORD_TYPE, label: ALL_QUOTA_RECORD_TYPE_LABEL }],
    default_days: DEFAULT_QUOTA_RECORD_DAYS,
    default_record_type: DEFAULT_QUOTA_RECORD_TYPE,
  };
}

export function buildQuotaRecordFiltersMeta(api: QuotaRecordFiltersApi): QuotaRecordFiltersMeta {
  return {
    days: api.days.map((value) => ({
      value: value as QuotaRecordDays,
      label: formatQuotaRecordDayLabel(value),
    })),
    record_types: [
      { value: ALL_QUOTA_RECORD_TYPE, label: ALL_QUOTA_RECORD_TYPE_LABEL },
      ...api.record_types,
    ] satisfies QuotaRecordTypeFilterUiOption[],
    default_days: api.default_days,
    default_record_type: DEFAULT_QUOTA_RECORD_TYPE,
  };
}

export function downloadQuotaRecordsCsv(blob: Blob) {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `配额记录-${new Date().toISOString().slice(0, 10)}.csv`;
  anchor.click();
  URL.revokeObjectURL(url);
}
