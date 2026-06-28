import { fetchPayOrders } from "@/api/billing";
import { paginatedListResult, usePaginatedQuery } from "@/hooks/usePaginatedQuery";
import { billingSortParams, type BillingSortState } from "@/lib/billing/sort";
import { queryKeys } from "@/lib/queries";
import type { PayOrderSortField } from "@/types/billing";

type UsePayOrdersOptions = {
  page: number;
  pageSize: number;
  sort: BillingSortState<PayOrderSortField>;
};

export function usePayOrders({ page, pageSize, sort }: UsePayOrdersOptions) {
  const { sortBy, order } = billingSortParams(sort, "created_at");
  const query = usePaginatedQuery({
    queryKey: queryKeys.payOrders(page, pageSize, sortBy, order),
    queryFn: () =>
      fetchPayOrders({
        page,
        page_size: pageSize,
        sort_by: sortBy,
        order,
      }),
    staleTime: 60_000,
    retry: false,
  });

  return {
    ...query,
    ...paginatedListResult(query, { page, pageSize }),
  };
}
