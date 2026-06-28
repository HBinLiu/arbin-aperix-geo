import { useQuery } from "@tanstack/react-query";

import { exportQuotaRecords, fetchQuotaRecordFilters, fetchQuotaRecords } from "@/api/billing";
import { paginatedListResult, usePaginatedQuery } from "@/hooks/usePaginatedQuery";
import { billingSortParams, type BillingSortState } from "@/lib/billing/sort";
import { queryKeys } from "@/lib/queries";
import type { QuotaRecordFilters, QuotaRecordSortField } from "@/types/billing";

type UseQuotaRecordsOptions = {
  page: number;
  pageSize: number;
  sort: BillingSortState<QuotaRecordSortField>;
  filters: QuotaRecordFilters;
  enabled?: boolean;
};

export function useQuotaRecordFilters() {
  return useQuery({
    queryKey: queryKeys.quotaRecordFilters,
    queryFn: fetchQuotaRecordFilters,
    staleTime: Infinity,
  });
}

export function useQuotaRecords({ page, pageSize, sort, filters, enabled = true }: UseQuotaRecordsOptions) {
  const { sortBy, order } = billingSortParams(sort, "created_at");
  const query = usePaginatedQuery({
    queryKey: queryKeys.quotaRecords(page, pageSize, sortBy, order, filters.days, filters.record_type),
    queryFn: () =>
      fetchQuotaRecords({
        page,
        page_size: pageSize,
        sort_by: sortBy,
        order,
        days: filters.days,
        record_type: filters.record_type,
      }),
    staleTime: 60_000,
    retry: false,
    enabled,
  });

  return {
    ...query,
    ...paginatedListResult(query, { page, pageSize }),
  };
}

export async function exportQuotaRecordsWithFilters(
  sort: BillingSortState<QuotaRecordSortField>,
  filters: QuotaRecordFilters,
): Promise<Blob> {
  const { sortBy, order } = billingSortParams(sort, "created_at");
  return exportQuotaRecords({
    sort_by: sortBy,
    order,
    days: filters.days,
    record_type: filters.record_type,
  });
}
